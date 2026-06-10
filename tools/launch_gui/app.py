"""Main window + entrypoint."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .backend import Backend, detect_backend
from . import ros2_graph_server
from .constants import (
    DEFAULT_ACTIVE_CHIPS,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    FILTER_CHIPS,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    RESTART_DELAY_MS,
    UPTIME_TICK_MS,
)
from .model import Launch, LogEntry
from .widgets import (
    CommandPalette,
    LaunchCard,
    LogsPanel,
    SectionHeader,
    Toast,
    WebEnginePage,
    make_green_dot,
    set_letter_spacing,
)


PKG_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PKG_DIR.parent / "assets"
TF_TREE_HTML = ASSETS_DIR / "tf_tree_visualizer.html"
ROS_GRAPH_HTML = ASSETS_DIR / "ros2_graph_explorer.html"
QSS_FILE = PKG_DIR / "style.qss"


def _load_qss() -> str:
    try:
        return QSS_FILE.read_text(encoding="utf-8")
    except OSError:
        return ""


class LaunchGui(QMainWindow):
    def __init__(self, backend: Backend) -> None:
        super().__init__()
        self.setWindowTitle("CobraFlex · Launch Manager")
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)

        self.backend = backend
        self.backend.on_state_changed = self._on_backend_state
        self.backend.on_log_line = self._on_backend_log

        self.launches: List[Launch] = self.backend.launches
        self.query: str = ""
        self.active_chips: Set[str] = set(DEFAULT_ACTIVE_CHIPS)
        self.selected_id: str = self.launches[0].id if self.launches else ""
        self.card_widgets: Dict[str, LaunchCard] = {}
        self._toasts: List[Toast] = []
        self._palette: Optional[CommandPalette] = None

        root = QWidget(); root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        outer.addWidget(self._build_env_strip())
        outer.addWidget(self._build_header())
        outer.addWidget(self._build_tab_bar())

        launches_page = QWidget()
        launches_page.setObjectName("root")
        lp = QVBoxLayout(launches_page)
        lp.setContentsMargins(0, 0, 0, 0); lp.setSpacing(0)
        lp.addWidget(self._build_filter())
        lp.addWidget(self._build_list(), 1)
        self.logs_panel = LogsPanel()
        self.logs_panel.clear_requested.connect(self._clear_logs)
        lp.addWidget(self.logs_panel)

        self.tf_tree_page = WebEnginePage(TF_TREE_HTML)
        self.ros_graph_page = WebEnginePage(ROS_GRAPH_HTML)

        self.stack = QStackedWidget()
        self.stack.addWidget(launches_page)
        self.stack.addWidget(self.tf_tree_page)
        self.stack.addWidget(self.ros_graph_page)
        outer.addWidget(self.stack, 1)

        self._rebuild_list()
        self._refresh_logs_subject()

        self.uptime_timer = QTimer(self)
        self.uptime_timer.timeout.connect(self._tick_uptime)
        self.uptime_timer.start(UPTIME_TICK_MS)

        self._install_shortcuts()

    # ─── Lifecycle ────────────────────────────────────────────────
    def closeEvent(self, e) -> None:
        self.backend.shutdown()
        super().closeEvent(e)

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._layout_toasts()

    # ─── Env strip ────────────────────────────────────────────────
    def _build_env_strip(self) -> QWidget:
        f = QFrame(); f.setObjectName("envStrip")
        h = QHBoxLayout(f); h.setContentsMargins(24, 4, 24, 4); h.setSpacing(8)

        domain = os.environ.get("ROS_DOMAIN_ID", "0")
        distro = os.environ.get("ROS_DISTRO", "jazzy")
        host = os.environ.get("HOSTNAME") or os.environ.get("COMPUTERNAME", "localhost")

        for txt, name in [
            ("ROS_DOMAIN_ID", "envLabel"), (domain, "envValue"),
            ("·", "envSep"),
            (distro, "envValue"),
            ("·", "envSep"),
            (host, "envValue"),
            ("·", "envSep"),
            (f"/opt/ros/{distro}", "envValue"),
        ]:
            lbl = QLabel(txt); lbl.setObjectName(name); h.addWidget(lbl)
        h.addStretch()
        ok_label = "● daemon: " + ("ok" if shutil.which("ros2") else "—")
        ok = QLabel(ok_label)
        ok.setObjectName("envOk" if shutil.which("ros2") else "envLabel")
        h.addWidget(ok)
        return f

    # ─── Header ───────────────────────────────────────────────────
    def _build_header(self) -> QWidget:
        f = QFrame(); f.setObjectName("hdr")
        h = QHBoxLayout(f); h.setContentsMargins(24, 14, 24, 12); h.setSpacing(14)

        left = QVBoxLayout(); left.setSpacing(2)
        eye = QLabel("COBRAFLEX · THESIS"); eye.setObjectName("hdrEyebrow")
        set_letter_spacing(eye, 1.6); left.addWidget(eye)
        title = QLabel("Launch Manager"); title.setObjectName("hdrTitle")
        left.addWidget(title)
        h.addLayout(left); h.addStretch()

        meta = QHBoxLayout(); meta.setSpacing(6)
        for txt, name in [("commit", "hdrMetaDim"), ("0cbd1ad", "hdrMetaMono"),
                          ("·", "hdrMetaDot"), ("jazzy", "hdrMetaMono")]:
            lbl = QLabel(txt); lbl.setObjectName(name); meta.addWidget(lbl)
        h.addLayout(meta)

        if self.backend.mode_label:
            mb = QLabel(self.backend.mode_label); mb.setObjectName("modeBadge")
            h.addWidget(mb)

        phase = QLabel("F3"); phase.setObjectName("phaseChipHdr")
        h.addWidget(phase)

        self.running_pill = QFrame(); self.running_pill.setObjectName("hdrRunning")
        rp = QHBoxLayout(self.running_pill); rp.setContentsMargins(10, 4, 12, 4); rp.setSpacing(6)
        rp.addWidget(make_green_dot())
        self.running_text = QLabel("0 running"); self.running_text.setObjectName("hdrRunningText")
        rp.addWidget(self.running_text)
        h.addWidget(self.running_pill)
        return f

    # ─── Tabs ─────────────────────────────────────────────────────
    def _build_tab_bar(self) -> QWidget:
        f = QFrame(); f.setObjectName("tabBar")
        h = QHBoxLayout(f); h.setContentsMargins(20, 0, 20, 0); h.setSpacing(2)
        self.tab_buttons: List[QPushButton] = []
        for i, label in enumerate(["Launches", "TF Tree", "ROS Graph"]):
            b = QPushButton(label); b.setObjectName("tab")
            b.setCheckable(True); b.setCursor(Qt.PointingHandCursor)
            b.setChecked(i == 0)
            b.clicked.connect(lambda _ck, idx=i: self._on_tab_changed(idx))
            self.tab_buttons.append(b)
            h.addWidget(b)
        h.addStretch()
        return f

    def _on_tab_changed(self, idx: int) -> None:
        for i, b in enumerate(self.tab_buttons):
            b.setChecked(i == idx)
        page = self.stack.widget(idx)
        if isinstance(page, WebEnginePage):
            page.initialize()
        self.stack.setCurrentIndex(idx)

    # ─── Filter bar ───────────────────────────────────────────────
    def _build_filter(self) -> QWidget:
        f = QFrame(); f.setObjectName("filterBar")
        h = QHBoxLayout(f); h.setContentsMargins(24, 10, 24, 10); h.setSpacing(12)

        self.search_wrap = QFrame(); self.search_wrap.setObjectName("searchWrap")
        self.search_wrap.setProperty("focused", "false")
        self.search_wrap.setFixedHeight(32); self.search_wrap.setMaximumWidth(320)
        sw = QHBoxLayout(self.search_wrap); sw.setContentsMargins(10, 0, 10, 0); sw.setSpacing(8)
        icon = QLabel("🔍"); icon.setObjectName("searchIcon"); sw.addWidget(icon)
        self.search_input = QLineEdit(); self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("Filter launches…")
        self.search_input.textChanged.connect(self._on_query_changed)
        self.search_input.installEventFilter(self)
        sw.addWidget(self.search_input)
        h.addWidget(self.search_wrap)

        chip_row = QHBoxLayout(); chip_row.setSpacing(6)
        self.chip_buttons: Dict[str, QPushButton] = {}
        for cid, label in FILTER_CHIPS:
            b = QPushButton(label); b.setObjectName("chip")
            b.setCursor(Qt.PointingHandCursor); b.setCheckable(True)
            b.setChecked(cid in self.active_chips)
            b.clicked.connect(lambda checked, c=cid: self._on_chip(c, checked))
            self.chip_buttons[cid] = b
            chip_row.addWidget(b)
        h.addLayout(chip_row); h.addStretch()

        self.stop_all_btn = QPushButton("■  Stop all")
        self.stop_all_btn.setObjectName("btnStopAll")
        self.stop_all_btn.setCursor(Qt.PointingHandCursor)
        self.stop_all_btn.clicked.connect(self._on_stop_all)
        self.stop_all_btn.setVisible(False)
        h.addWidget(self.stop_all_btn)

        self.count_pill = QLabel(); self.count_pill.setObjectName("countPill")
        h.addWidget(self.count_pill)
        return f

    def eventFilter(self, obj, ev):
        if obj is self.search_input:
            if ev.type() == QEvent.Type.FocusIn:
                self.search_wrap.setProperty("focused", "true")
            elif ev.type() == QEvent.Type.FocusOut:
                self.search_wrap.setProperty("focused", "false")
            else:
                return super().eventFilter(obj, ev)
            self.search_wrap.style().unpolish(self.search_wrap)
            self.search_wrap.style().polish(self.search_wrap)
        return super().eventFilter(obj, ev)

    # ─── Launch list ──────────────────────────────────────────────
    def _build_list(self) -> QWidget:
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.list_container = QWidget(); self.list_container.setObjectName("root")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(24, 16, 24, 12); self.list_layout.setSpacing(8)
        self.scroll.setWidget(self.list_container)
        return self.scroll

    def _rebuild_list(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        self.card_widgets = {}

        filtered = self._filter_launches()
        starred = [l for l in filtered if l.starred]
        rest = [l for l in filtered if not l.starred]

        if not filtered:
            empty = QLabel("No launches match the current filters.")
            empty.setObjectName("empty"); empty.setAlignment(Qt.AlignCenter)
            self.list_layout.addWidget(empty)
        else:
            if starred:
                self.list_layout.addWidget(SectionHeader("PINNED", len(starred), glyph="⭐"))
                for l in starred:
                    self._add_card(l)
                self.list_layout.addSpacing(10)
                self.list_layout.addWidget(SectionHeader("ALL LAUNCHES", len(rest)))
            for l in rest:
                self._add_card(l)
        self.list_layout.addStretch()

        self.count_pill.setText(f"✓  {len(filtered)} of {len(self.launches)} launches")
        self._refresh_running_pill()

    def _add_card(self, launch: Launch) -> None:
        card = LaunchCard(launch)
        card.set_selected(launch.id == self.selected_id)
        card.selected_signal.connect(self._on_select)
        card.run_signal.connect(self._on_run)
        card.stop_signal.connect(self._on_stop)
        card.restart_signal.connect(self._on_restart)
        card.star_signal.connect(self._on_star)
        self.card_widgets[launch.id] = card
        self.list_layout.addWidget(card)

    def _filter_launches(self) -> List[Launch]:
        q = self.query.strip().lower()
        out = []
        for l in self.launches:
            tags = l.tags if l.tags else ["_untagged"]
            if not any(t in self.active_chips for t in tags):
                continue
            if q and not (q in l.pkg.lower() or q in l.name.lower() or q in l.desc.lower()):
                continue
            out.append(l)
        return out

    def _refresh_running_pill(self) -> None:
        n = sum(1 for l in self.launches if l.state == "running")
        self.running_text.setText(f"{n} running")
        if hasattr(self, "stop_all_btn"):
            self.stop_all_btn.setVisible(n > 0)
            self.stop_all_btn.setText(f"■  Stop all ({n})")

    # ─── Logs ─────────────────────────────────────────────────────
    def _refresh_logs_subject(self) -> None:
        self.logs_panel.set_launch(self._selected_launch())

    def _selected_launch(self) -> Optional[Launch]:
        for l in self.launches:
            if l.id == self.selected_id:
                return l
        return None

    def _clear_logs(self) -> None:
        sel = self._selected_launch()
        if sel:
            sel.logs.clear()
        self._refresh_logs_subject()

    # ─── Backend callbacks ────────────────────────────────────────
    def _on_backend_state(self, launch: Launch) -> None:
        prev_state = getattr(launch, "_prev_observed_state", None)
        if launch.id in self.card_widgets:
            self.card_widgets[launch.id].refresh()
        self._refresh_running_pill()
        if launch.id == self.selected_id:
            self.logs_panel.refresh_live_pill()

        if prev_state != launch.state:
            if launch.state == "running":
                self.show_toast("ok", f"{launch.pkg} / {launch.name} started",
                                f"PID {launch.pid}")
            elif launch.state == "failed":
                self.show_toast("err", f"{launch.pkg} / {launch.name} failed",
                                f"exit {launch.exit_code}")
            elif launch.state == "stopped" and prev_state == "running":
                self.show_toast("stop", f"{launch.pkg} / {launch.name} stopped")
        launch._prev_observed_state = launch.state

    def _on_backend_log(self, launch: Launch, entry: LogEntry) -> None:
        if launch.id == self.selected_id:
            self.logs_panel.append_entry(entry)

    # ─── User actions ─────────────────────────────────────────────
    def _on_query_changed(self, text: str) -> None:
        self.query = text
        self._rebuild_list()

    def _on_chip(self, cid: str, checked: bool) -> None:
        if checked:
            self.active_chips.add(cid)
        else:
            self.active_chips.discard(cid)
        self._rebuild_list()

    def _on_select(self, launch_id: str) -> None:
        if self.selected_id == launch_id:
            return
        prev = self.card_widgets.get(self.selected_id)
        if prev:
            prev.set_selected(False)
        self.selected_id = launch_id
        nxt = self.card_widgets.get(launch_id)
        if nxt:
            nxt.set_selected(True)
        self._refresh_logs_subject()

    def _on_run(self, launch_id: str) -> None:
        launch = next((l for l in self.launches if l.id == launch_id), None)
        if launch is None:
            return
        self.backend.run(launch)
        self.selected_id = launch_id
        for lid, card in self.card_widgets.items():
            card.set_selected(lid == launch_id)
        self._refresh_logs_subject()

    def _on_stop(self, launch_id: str) -> None:
        launch = next((l for l in self.launches if l.id == launch_id), None)
        if launch is not None:
            self.backend.stop(launch)

    def _on_restart(self, launch_id: str) -> None:
        launch = next((l for l in self.launches if l.id == launch_id), None)
        if launch is None:
            return
        self.backend.stop(launch)
        QTimer.singleShot(RESTART_DELAY_MS, lambda l=launch: self.backend.run(l))
        self.show_toast("info", f"{launch.pkg} / {launch.name} restarting")

    def _on_star(self, launch_id: str) -> None:
        launch = next((l for l in self.launches if l.id == launch_id), None)
        if launch is None:
            return
        launch.starred = not launch.starred
        self._rebuild_list()

    def _on_stop_all(self) -> None:
        n = 0
        for l in self.launches:
            if l.state == "running":
                self.backend.stop(l)
                n += 1
        if n:
            self.show_toast("stop", f"Stopped {n} launch{'es' if n != 1 else ''}")

    # ─── Toasts ───────────────────────────────────────────────────
    def show_toast(self, kind: str, title: str, subtitle: Optional[str] = None) -> None:
        toast = Toast(kind, title, subtitle, parent=self)
        toast.dismissed.connect(lambda t=toast: self._remove_toast(t))
        self._toasts.append(toast)
        toast.show()
        self._layout_toasts()

    def _remove_toast(self, toast: Toast) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
        self._layout_toasts()

    def _layout_toasts(self) -> None:
        margin = 16
        spacing = 8
        y = self.height() - margin
        for toast in reversed(self._toasts):
            toast.adjustSize()
            x = self.width() - toast.width() - margin
            y -= toast.height()
            toast.move(x, y)
            y -= spacing
            toast.raise_()

    # ─── Command palette ──────────────────────────────────────────
    def _open_palette(self) -> None:
        if self._palette is None:
            self._palette = CommandPalette(self)
            self._palette.triggered.connect(self._on_palette_action)
        self._palette.open_with(self.launches)

    def _on_palette_action(self, data: dict) -> None:
        kind = data.get("kind")
        if kind == "action":
            aid = data.get("action_id")
            if aid == "stop-all":
                self._on_stop_all()
            elif aid == "clear-logs":
                self._clear_logs()
        elif kind == "run":
            self._on_run(data.get("launch_id", ""))
        elif kind == "stop":
            self._on_stop(data.get("launch_id", ""))

    # ─── Keyboard shortcuts ───────────────────────────────────────
    def _install_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+K"), self, activated=self._open_palette)
        QShortcut(QKeySequence("Meta+K"), self, activated=self._open_palette)
        QShortcut(QKeySequence("/"),       self, activated=self._focus_search)
        QShortcut(QKeySequence("R"),       self, activated=self._run_selected)
        QShortcut(QKeySequence("S"),       self, activated=self._stop_selected)
        QShortcut(QKeySequence("Escape"),  self, activated=self._on_escape)

    def _focus_search(self) -> None:
        if self.stack.currentIndex() == 0:
            self.search_input.setFocus()
            self.search_input.selectAll()

    def _run_selected(self) -> None:
        l = self._selected_launch()
        if l and l.state != "running":
            self._on_run(l.id)

    def _stop_selected(self) -> None:
        l = self._selected_launch()
        if l and l.state == "running":
            self._on_stop(l.id)

    def _on_escape(self) -> None:
        if self._palette and self._palette.isVisible():
            self._palette.close()

    # ─── Uptime tick ──────────────────────────────────────────────
    def _tick_uptime(self) -> None:
        for l in self.launches:
            if l.state == "running":
                l.uptime += 1
                card = self.card_widgets.get(l.id)
                if card:
                    card.refresh()


# ─── Entrypoint ──────────────────────────────────────────────────────────────

def _workspace_root() -> Path:
    # tools/launch_gui/app.py -> tools/launch_gui -> tools -> repo
    return PKG_DIR.parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="CobraFlex Launch Manager")
    parser.add_argument("--mock", action="store_true",
                        help="Force mock backend (no ROS2 required)")
    parser.add_argument("--workspace", type=Path, default=None,
                        help="Workspace root (default: repo root inferred from this script)")
    args, _ = parser.parse_known_args()

    backend = detect_backend(args.mock, args.workspace or _workspace_root())
    backend.setup()

    ros2_graph_server.start()

    app = QApplication(sys.argv)
    app.setStyleSheet(_load_qss())
    win = LaunchGui(backend)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
