#!/usr/bin/env bash
# setup_deploy_env.sh — one `source` to make the Phase-5 RL chain runnable on the
# physical CobraFlex (Jetson / L4T R36, ROS 2 Humble). See docs/17 §2 item 6.
#
#     source ~/MT-SE4AI-Safe-RL-Cobraflex/scripts/setup_deploy_env.sh
#     ros2 launch cobraflex_rl deploy_cobraflex.launch.py checkpoint:=... mode:=monitoring
#
# It does three things, in this order, and each one is load-bearing:
#
#   1. Sources ROS 2 Humble + the car's colcon overlay.
#   2. Puts the inference venv on PYTHONPATH — NOT on PATH, and the venv is NOT
#      activated. The installed node scripts carry a `#!/usr/bin/python3` shebang,
#      so activation would be silently ignored; PYTHONPATH is what actually reaches
#      them. The venv is --system-site-packages, so this is purely additive
#      (torch + stable-baselines3 + gymnasium + numpy 1.26.4) and rclpy / cv_bridge
#      / cv2 keep working — verified 2026-08-04.
#   3. LD_PRELOADs the OpenBLAS that ships inside torch. This is the non-obvious
#      one. Ubuntu 22.04's /usr/lib/aarch64-linux-gnu/libopenblas.so.0 has no
#      `sbgemm_` (bf16 GEMM, OpenBLAS >= 0.3.22); torch's bundled copy exports it.
#      Whichever is loaded FIRST wins for the whole process, and the system OpenCV
#      pulls in the system one — so importing cv2 before torch (exactly what the
#      node chain does) makes `import torch` die with
#      `undefined symbol: sbgemm_`. Preloading torch's copy makes the outcome
#      independent of import order. Do NOT use LD_LIBRARY_PATH instead: that also
#      overrides libgomp from torch/lib and breaks numpy's sanity check.
#
# Reversal: unset the two vars, or `rm -rf "$COBRAFLEX_RL_VENV"` to drop the venv.

COBRAFLEX_RL_VENV="${COBRAFLEX_RL_VENV:-$HOME/rl_deploy_venv}"
COBRAFLEX_ROS_WS="${COBRAFLEX_ROS_WS:-$HOME/ros2_ws}"
_py_ver="python3.10"

if [ -f /opt/ros/humble/setup.bash ]; then
    # shellcheck disable=SC1091
    source /opt/ros/humble/setup.bash
else
    echo "setup_deploy_env: /opt/ros/humble not found — is this the car host?" >&2
fi

if [ -f "$COBRAFLEX_ROS_WS/install/setup.bash" ]; then
    # shellcheck disable=SC1091
    source "$COBRAFLEX_ROS_WS/install/setup.bash"
else
    echo "setup_deploy_env: no colcon overlay at $COBRAFLEX_ROS_WS/install — run colcon build" >&2
fi

_venv_site="$COBRAFLEX_RL_VENV/lib/$_py_ver/site-packages"
if [ -d "$_venv_site" ]; then
    export PYTHONPATH="$_venv_site${PYTHONPATH:+:$PYTHONPATH}"

    _torch_blas="$_venv_site/torch/lib/libopenblas.so.0"
    if [ -f "$_torch_blas" ]; then
        export LD_PRELOAD="$_torch_blas${LD_PRELOAD:+:$LD_PRELOAD}"
    else
        echo "setup_deploy_env: torch present but $_torch_blas is missing;" >&2
        echo "                  'import torch' will likely fail on sbgemm_." >&2
    fi
else
    echo "setup_deploy_env: inference venv not found at $COBRAFLEX_RL_VENV." >&2
    echo "                  rl_policy_node cannot run. Create it with:" >&2
    echo "                    python3 -m virtualenv --system-site-packages $COBRAFLEX_RL_VENV" >&2
    echo "                    $COBRAFLEX_RL_VENV/bin/python -m pip install \\" >&2
    echo "                        torch --index-url https://download.pytorch.org/whl/cpu" >&2
    echo "                    $COBRAFLEX_RL_VENV/bin/python -m pip install stable-baselines3 'numpy==1.26.4'" >&2
fi

unset _py_ver _venv_site _torch_blas
