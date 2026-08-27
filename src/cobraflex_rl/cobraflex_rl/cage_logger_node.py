"""
cage_logger_node — subscribe to /cage_status, write CSV via cage.logger.

Wraps the existing pure-Python cage.logger.CageLogger by converting
each incoming CageStatus message into the result-dict shape that
CageLogger expects, then calling add_cycle(). The CSV schema is
therefore identical to the one cage_node.step() tests emit, which
keeps the offline analysis tooling unified across in-Python tests and
ROS2 runs.

A run is started on first /cage_status message and closed on shutdown.
Output directory is parameterised; one CSV file per run.

On the physical platform (``platform:=physical``) the run also records its
reproducibility provenance — git commit, cage YAML hash, policy checkpoint
hash and the deployed launch contract — written at start-up as well as on
close, so a run that dies still says what produced it.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _bootstrap_cage_import() -> None:
    """Make ``cage`` importable when the repo isn't pip-installed (path walk-up)."""
    try:
        import cage.logger  # noqa: F401
        return
    except ImportError:
        pass
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "cage" / "logger.py"
        if candidate.is_file():
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))
            return


_bootstrap_cage_import()

import rclpy  # noqa: E402
from rclpy.clock import Clock  # noqa: E402
from rclpy.node import Node  # noqa: E402
from rclpy.qos import QoSPresetProfiles  # noqa: E402
from std_msgs.msg import Float64MultiArray  # noqa: E402

from cage.logger import CageLogger  # noqa: E402
from cobraflex_safety_msgs.msg import CageStatus  # noqa: E402

from .run_io import (  # noqa: E402
    CONTRACT_KEYS,
    physical_run_metadata,
    resolve_repo_path,
)


class CageLoggerNode(Node):
    """/cage_status → CSV adapter around the pure-Python CageLogger."""

    def __init__(self) -> None:
        super().__init__("cage_logger")

        self.declare_parameter("output_dir", "")
        self.declare_parameter("run_id", "")
        self.declare_parameter("cage_status_topic", "/cage_status")
        self.declare_parameter("state_obs_topic", "/state_obs")
        # Stamp the cage operating mode into every CSV row. CageStatus.msg
        # does not carry mode (it's a node-level property, not per-cycle),
        # so the logger reads it from a launch parameter aligned with
        # safety_cage's `mode` parameter.
        self.declare_parameter("cage_mode", "enforcement")

        # Reproducibility provenance (CLAUDE.md's rule for
        # experiments/{sim,physical}/runs). Empty `platform` keeps the legacy
        # four-field metadata.json, so the F2 sim pipeline is untouched; the
        # Phase-5 deploy launch passes "physical" and the paths below.
        self.declare_parameter("platform", "")
        self.declare_parameter("cage_yaml", "")
        self.declare_parameter("policy_checkpoint", "")
        self.declare_parameter("rectify_calibration", "")
        for key in CONTRACT_KEYS:
            self.declare_parameter(f"contract.{key}", "")

        output_dir = (
            self.get_parameter("output_dir").get_parameter_value().string_value
            or "experiments/sim/runs"
        )
        run_id = self.get_parameter("run_id").get_parameter_value().string_value or (
            "ros_run_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        )

        out_path = (Path(output_dir).expanduser().resolve() / run_id)
        self._cage_mode = (
            self.get_parameter("cage_mode").get_parameter_value().string_value
            or "enforcement"
        )
        self._cage_logger: Optional[CageLogger] = CageLogger(
            out_path, run_id=run_id, metadata=self._build_metadata(run_id)
        )
        # Written NOW, not only on close: the 18.08.2026 power-cycle left a run
        # with a CSV and no metadata.json at all (circuit_survey/REPAIR_NOTE).
        self._cage_logger.write_metadata()
        self.get_logger().info(
            f"Writing cage CSV to {self._cage_logger.cage_status_path} "
            f"(mode={self._cage_mode})."
        )

        self._last_state: dict = {}

        reliable_qos = QoSPresetProfiles.SYSTEM_DEFAULT.value
        sensor_qos = QoSPresetProfiles.SENSOR_DATA.value
        self.create_subscription(
            CageStatus,
            self.get_parameter("cage_status_topic").value,
            self._on_status,
            reliable_qos,
        )
        self.create_subscription(
            Float64MultiArray,
            self.get_parameter("state_obs_topic").value,
            self._on_state_obs,
            sensor_qos,
        )

        # Watchdog: surface silent upstream failures. The pipeline is
        # callback-chained (lane_perception → pd → cage → logger); a stuck
        # upstream node leaves the CSV with only its header and no error
        # anywhere. Tick every 5 s on the wall clock (NOT sim time, so it
        # also fires while Gazebo is paused or has died).
        self._cycle_count_at_last_tick = 0
        self.create_timer(5.0, self._on_watchdog_tick, clock=Clock())

    def _build_metadata(self, run_id: str) -> dict:
        """Run metadata: legacy four fields, or the full physical provenance."""
        platform = self.get_parameter("platform").get_parameter_value().string_value
        if platform != "physical":
            return {"mode": self._cage_mode}

        def _param(name: str) -> str:
            return self.get_parameter(name).get_parameter_value().string_value

        # An empty cage_yaml means the cage node resolved it by walking up to
        # the repo's cage/cage.yaml; resolve it the same way so the hash is of
        # the file actually loaded, not of nothing.
        cage_yaml = _param("cage_yaml") or resolve_repo_path("cage/cage.yaml")
        contract = {
            key: value
            for key in CONTRACT_KEYS
            if (value := _param(f"contract.{key}"))
        }
        metadata = physical_run_metadata(
            run_id,
            self._cage_mode,
            cage_yaml=cage_yaml,
            policy_checkpoint=_param("policy_checkpoint") or None,
            rectify_calibration=_param("rectify_calibration") or None,
            contract=contract,
            status="running",
        )
        self.get_logger().info(
            "Run provenance: commit %s, cage.yaml %s, checkpoint %s."
            % (
                metadata["git_commit"][:8],
                (metadata["cage_yaml_hash"] or "MISSING")[:8],
                (metadata["policy_checkpoint_hash"] or "MISSING")[:8],
            )
        )
        for field in ("cage_yaml_hash", "policy_checkpoint_hash"):
            if metadata[field] is None:
                self.get_logger().warning(
                    "%s could not be computed — this run's evidence is NOT "
                    "self-describing and cannot be cited without a hand-written "
                    "provenance note." % field
                )
        return metadata

    def _on_state_obs(self, msg: Float64MultiArray) -> None:
        """Cache the latest state sample so each CSV row carries ey/epsi/speed."""
        if len(msg.data) < 7:
            return
        self._last_state = {
            "ey": float(msg.data[0]),
            "epsi": float(msg.data[1]),
            "speed": float(msg.data[2]),
            "kappa_ahead": float(msg.data[3]),
        }

    def _on_status(self, msg: CageStatus) -> None:
        """Convert one CageStatus message into CageLogger's result-dict shape."""
        if self._cage_logger is None:
            return

        stamp_s = float(msg.header.stamp.sec) + float(msg.header.stamp.nanosec) * 1e-9
        result = {
            "current_time": stamp_s,
            "mode": self._cage_mode,
            "cage_version": msg.yaml_version,
            "raw_action": (float(msg.action_raw.angular.z), float(msg.action_raw.linear.x)),
            "safe_action": (float(msg.action_safe.angular.z), float(msg.action_safe.linear.x)),
            "emergency": bool(msg.emergency_mode),
            "interventions": [{"rule": r, "reason": "", "metadata": {}} for r in msg.rules_triggered],
            "cycles_since_last_state": int(msg.cycles_since_last_state),
            "oscillation_persistent": bool(msg.osc_persistent),
            "oscillation_rates_hz": dict(zip(msg.osc_rule_ids, msg.oscillation_rates_hz)),
            "state": dict(self._last_state),
        }
        self._cage_logger.add_cycle(result)

    def _on_watchdog_tick(self) -> None:
        if self._cage_logger is None:
            return
        count = self._cage_logger.cycle_count
        delta = count - self._cycle_count_at_last_tick
        self._cycle_count_at_last_tick = count
        if count == 0:
            self.get_logger().warning(
                "No /cage_status messages received yet — upstream pipeline "
                "(lane_perception → pd_baseline → safety_cage) is likely "
                "stuck. CSV at %s has only its header."
                % str(self._cage_logger.cage_status_path)
            )
        elif delta == 0:
            self.get_logger().warning(
                "No new /cage_status in the last 5 s (cycle_count stuck at "
                "%d). Upstream may have crashed mid-run." % count
            )
        else:
            self.get_logger().info(
                "cage_logger alive: %d cycles total (+%d in last 5 s)."
                % (count, delta)
            )

    def destroy_node(self) -> bool:
        """Flush and close the CSV before tearing the node down."""
        if self._cage_logger is not None:
            self._cage_logger.write_metadata(status="completed")
            self._cage_logger.close()
            self.get_logger().info(
                f"Closed cage_logger after {self._cage_logger.cycle_count} cycles."
            )
            self._cage_logger = None
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = CageLoggerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
