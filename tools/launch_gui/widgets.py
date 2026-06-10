"""All Qt widget classes used by the LaunchGui."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .constants import (
    LOG_LEVELS,
    LOG_LEVEL_COLORS,
    LOGS_PANEL_MAX_HEIGHT,
    PALETTE_HEIGHT,
    PALETTE_WIDTH,
    PHASE_COLORS,
    TOAST_DURATION_MS,
)
from .model import Launch, LogEntry, build_command


# Optional WebEngine — degrade gracefully on Essentials-only installs.
try:
    from PySide6.QtCore import QUrl
    from PySide6.QtWebEngineCore import QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView
    _WEBENGINE_AVAILABLE = True
except ImportError:
    _WEBENGINE_AVAILABLE = False


# ─── Tiny helpers ───────────────────────────────────────────────────────────

def make_green_dot() -> QFrame:
    """Green dot with subtle halo (static; approximates a pulsing live indicator)."""
    halo = QFrame()
    halo.setObjectName("dotHalo")
    halo.setFixedSize(14, 14)
    dot = QFrame(halo)
    dot.setObjectName("dotGreen")
    dot.setFixedSize(8, 8)
    dot.move(3, 3)
    return halo


def make_grey_dot() -> QFrame:
    dot = QFrame()
    dot.setObjectName("dotGrey")
    dot.setFixedSize(8, 8)
    return dot


def make_red_dot() -> QFrame:
    halo = QFrame()
    halo.setObjectName("dotRedHalo")
    halo.setFixedSize(14, 14)
    dot = QFrame(halo)
    dot.setObjectName("dotRed")
    dot.setFixedSize(8, 8)
    dot.move(3, 3)
    return halo


def make_phase_chip(phase: str) -> QLabel:
    lbl = QLabel(phase)
    c = PHASE_COLORS.get(phase, PHASE_COLORS["F3"])
    lbl.setStyleSheet(
        f"background: {c['bg']}; color: {c['fg']}; "
        f"border: 1px solid {c['bd']}; border-radius: 4px; "
        f"padding: 1px 7px; font-size: 10px; font-weight: 700;"
    )
    return lbl


def set_letter_spacing(widget, value: float) -> None:
    f = widget.font()
    f.setLetterSpacing(QFont.AbsoluteSpacing, value)
    widget.setFont(f)


def _restyle(widget) -> None:
    """Force QSS reapply after a dynamic property changed."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


# ─── Section header ─────────────────────────────────────────────────────────

class SectionHeader(QFrame):
    def __init__(self, label: str, count: int, glyph: str = "") -> None:
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 6, 0, 6)
        h.setSpacing(8)
        if glyph:
            g = QLabel(glyph); g.setObjectName("sectionGlyph"); h.addWidget(g)
        lab = QLabel(label); lab.setObjectName("sectionLabel")
        set_letter_spacing(lab, 1.4)
        h.addWidget(lab)
        cnt = QLabel(str(count)); cnt.setObjectName("sectionCount")
        h.addWidget(cnt)
        rule = QFrame(); rule.setObjectName("sectionRule")
        rule.setFixedHeight(1)
        rule.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        h.addWidget(rule, 1)


# ─── Per-arg editor ─────────────────────────────────────────────────────────

class ArgRow(QFrame):
    """One launch-arg editor row. Kind in {bool, enum, number, string}."""
    value_changed = Signal()

    def __init__(self, arg: dict) -> None:
        super().__init__()
        self.arg = arg
        self._suppress = False
        self._bool_buttons: Dict[str, QPushButton] = {}
        self.setObjectName("argRow")

        h = QHBoxLayout(self)
        h.setContentsMargins(8, 4, 8, 4)
        h.setSpacing(10)

        key = QLabel(arg["key"]); key.setObjectName("argKey")
        key.setMinimumWidth(140)
        h.addWidget(key)

        kind = arg.get("kind", "string")
        if kind == "bool":
            self.editor = self._make_bool_editor()
        elif kind == "enum":
            self.editor = self._make_enum_editor()
        else:
            self.editor = self._make_text_editor()
        h.addWidget(self.editor, 1)

        self.mod_indicator = QLabel("")
        self.mod_indicator.setObjectName("argMod")
        self.mod_indicator.setFixedWidth(14)
        self.mod_indicator.setAlignment(Qt.AlignCenter)
        h.addWidget(self.mod_indicator)

        if arg.get("help"):
            self.setToolTip(f"{arg['key']} — {arg['help']}")
        self._refresh_modified()

    def _make_bool_editor(self) -> QWidget:
        wrap = QFrame(); wrap.setObjectName("boolSeg")
        h = QHBoxLayout(wrap); h.setContentsMargins(2, 2, 2, 2); h.setSpacing(2)
        for val in ("true", "false"):
            b = QPushButton(val); b.setObjectName("boolSegBtn")
            b.setCheckable(True)
            b.setChecked(self.arg["value"] == val)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _ck, v=val: self._set_bool(v))
            self._bool_buttons[val] = b
            h.addWidget(b)
        return wrap

    def _make_enum_editor(self) -> QComboBox:
        cb = QComboBox(); cb.setObjectName("argEnum")
        cb.addItems(self.arg.get("options", []))
        cb.setCurrentText(self.arg["value"])
        cb.currentTextChanged.connect(self._set_value)
        return cb

    def _make_text_editor(self) -> QLineEdit:
        le = QLineEdit(self.arg["value"]); le.setObjectName("argText")
        le.textChanged.connect(self._set_value)
        return le

    def _set_bool(self, v: str) -> None:
        for k, btn in self._bool_buttons.items():
            btn.setChecked(k == v)
        self._set_value(v)

    def _set_value(self, v: str) -> None:
        if self._suppress:
            return
        self.arg["value"] = v
        self._refresh_modified()
        self.value_changed.emit()

    def _refresh_modified(self) -> None:
        modified = self.arg["value"] != self.arg.get("default", "")
        self.mod_indicator.setText("~" if modified else "")

    def refresh_from_arg(self) -> None:
        """Re-read self.arg['value'] and update the editor without firing signals."""
        self._suppress = True
        try:
            kind = self.arg.get("kind", "string")
            v = self.arg["value"]
            if kind == "bool":
                for k, btn in self._bool_buttons.items():
                    btn.setChecked(k == v)
            elif kind == "enum":
                self.editor.setCurrentText(v)
            else:
                self.editor.setText(v)
            self._refresh_modified()
        finally:
            self._suppress = False


# ─── Expandable section (command + args + presets) ──────────────────────────

class ExpandableSection(QFrame):
    """Per-card expanded panel: live command preview + args editor + presets.

    Args edits mutate `launch.args[i]["value"]` directly; the next backend.run()
    will pick them up via build_command()/args_to_overrides().
    """
    args_changed = Signal()

    def __init__(self, launch: Launch) -> None:
        super().__init__()
        self.launch = launch
        self.setObjectName("expandable")
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 12, 14, 14)
        v.setSpacing(12)

        # COMMAND
        cmd_hd = QHBoxLayout(); cmd_hd.setSpacing(8)
        cmd_label = QLabel("❯_  COMMAND"); cmd_label.setObjectName("expandLabel")
        set_letter_spacing(cmd_label, 1.2)
        cmd_hd.addWidget(cmd_label); cmd_hd.addStretch()
        copy_btn = QPushButton("Copy"); copy_btn.setObjectName("btnGhost")
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.clicked.connect(self._copy_command)
        cmd_hd.addWidget(copy_btn)
        v.addLayout(cmd_hd)

        self.cmd_box = QLabel(build_command(launch))
        self.cmd_box.setObjectName("cmdBox")
        self.cmd_box.setWordWrap(True)
        self.cmd_box.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self.cmd_box)

        # ARGUMENTS
        self.arg_rows: List[ArgRow] = []
        if launch.args:
            args_hd = QHBoxLayout()
            args_label = QLabel("◆  ARGUMENTS"); args_label.setObjectName("expandLabel")
            set_letter_spacing(args_label, 1.2)
            args_hd.addWidget(args_label); args_hd.addStretch()
            reset_btn = QPushButton("Reset"); reset_btn.setObjectName("btnGhost")
            reset_btn.setCursor(Qt.PointingHandCursor)
            reset_btn.clicked.connect(self._reset_args)
            args_hd.addWidget(reset_btn)
            v.addLayout(args_hd)
            for a in launch.args:
                row = ArgRow(a)
                row.value_changed.connect(self._on_arg_changed)
                self.arg_rows.append(row)
                v.addWidget(row)
        else:
            empty = QLabel("(no declared arguments)")
            empty.setStyleSheet(
                "color: #6e7681; font-size: 11px; font-style: italic; padding: 4px 8px;"
            )
            v.addWidget(empty)

        # PRESETS
        if launch.args:
            presets_label = QLabel("⚡  PRESETS"); presets_label.setObjectName("expandLabel")
            set_letter_spacing(presets_label, 1.2)
            v.addWidget(presets_label)
            self.preset_row = QHBoxLayout()
            self.preset_row.setSpacing(6)
            v.addLayout(self.preset_row)
            self._rebuild_presets()

    def _rebuild_presets(self) -> None:
        # Clear and rebuild — needed after Save as preset adds one.
        while self.preset_row.count():
            item = self.preset_row.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        for p in self.launch.presets:
            pb = QPushButton(p["name"]); pb.setObjectName("presetPill")
            pb.setCursor(Qt.PointingHandCursor)
            pb.clicked.connect(lambda _ck, preset=p: self._apply_preset(preset))
            self.preset_row.addWidget(pb)
        save_btn = QPushButton("+ Save current"); save_btn.setObjectName("presetSave")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save_preset)
        self.preset_row.addWidget(save_btn)
        self.preset_row.addStretch()

    def _on_arg_changed(self) -> None:
        self.cmd_box.setText(build_command(self.launch))
        self.args_changed.emit()

    def _copy_command(self) -> None:
        cb = QApplication.clipboard()
        if cb is not None:
            cb.setText(build_command(self.launch))

    def _reset_args(self) -> None:
        for a in self.launch.args:
            a["value"] = a.get("default", "")
        for row in self.arg_rows:
            row.refresh_from_arg()
        self._on_arg_changed()

    def _apply_preset(self, preset: dict) -> None:
        for k, v in preset.get("args", {}).items():
            for a in self.launch.args:
                if a["key"] == k:
                    a["value"] = v
                    break
        for row in self.arg_rows:
            row.refresh_from_arg()
        self._on_arg_changed()

    def _save_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "Save preset",
                                        "Name for the new preset:")
        if not ok or not name.strip():
            return
        name = name.strip()
        # Replace existing preset with same name, else append.
        args_snapshot = {a["key"]: a["value"] for a in self.launch.args
                         if a.get("value") != a.get("default")}
        if not args_snapshot:
            return
        existing = next((p for p in self.launch.presets if p["name"] == name), None)
        if existing is not None:
            existing["args"] = args_snapshot
        else:
            self.launch.presets.append({"name": name, "args": args_snapshot})
        self._rebuild_presets()


# ─── Launch card ────────────────────────────────────────────────────────────

class LaunchCard(QFrame):
    selected_signal = Signal(str)
    run_signal = Signal(str)
    stop_signal = Signal(str)
    restart_signal = Signal(str)
    star_signal = Signal(str)

    def __init__(self, launch: Launch) -> None:
        super().__init__()
        self.launch = launch
        self.setProperty("role", "card")
        self.setProperty("running", "true" if launch.state == "running" else "false")
        self.setProperty("failed", "true" if launch.state == "failed" else "false")
        self.setProperty("selected", "false")
        self.setProperty("expanded", "false")
        self.setCursor(Qt.PointingHandCursor)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        top_widget = QWidget()
        top = QHBoxLayout(top_widget)
        top.setContentsMargins(14, 14, 14, 12)
        top.setSpacing(16)

        col = QVBoxLayout()
        col.setSpacing(3)
        col.setContentsMargins(0, 0, 0, 0)

        l1 = QHBoxLayout()
        l1.setSpacing(8)
        l1.setContentsMargins(0, 0, 0, 0)

        self.expand_btn = QPushButton("▸"); self.expand_btn.setObjectName("expandBtn")
        self.expand_btn.setProperty("open", "false")
        self.expand_btn.setCursor(Qt.PointingHandCursor)
        self.expand_btn.setFlat(True)
        self.expand_btn.setToolTip("Show command and arguments")
        self.expand_btn.clicked.connect(self._toggle_expand)
        l1.addWidget(self.expand_btn)

        self.star_btn = QPushButton("⭐" if launch.starred else "☆")
        self.star_btn.setObjectName("cardStar")
        self.star_btn.setProperty("starred", "true" if launch.starred else "false")
        self.star_btn.setCursor(Qt.PointingHandCursor)
        self.star_btn.setFlat(True)
        self.star_btn.setToolTip("Pin / unpin")
        self.star_btn.clicked.connect(lambda: self.star_signal.emit(self.launch.id))
        l1.addWidget(self.star_btn)

        if launch.phase:
            l1.addWidget(make_phase_chip(launch.phase))
        pkg = QLabel(launch.pkg); pkg.setObjectName("cardPkg"); l1.addWidget(pkg)
        sl = QLabel("/"); sl.setObjectName("cardSlash"); l1.addWidget(sl)
        nm = QLabel(launch.name); nm.setObjectName("cardName"); l1.addWidget(nm)
        if launch.file_format == "xml":
            fmt = QLabel("xml"); fmt.setObjectName("cardFmt"); l1.addWidget(fmt)
        if launch.args:
            args_badge = QLabel(f"{len(launch.args)} args")
            args_badge.setObjectName("cardArgsBadge")
            l1.addWidget(args_badge)
        l1.addStretch()
        col.addLayout(l1)

        desc = QLabel(launch.desc); desc.setObjectName("cardDesc"); desc.setWordWrap(True)
        col.addWidget(desc)

        # Crash autopsy snippet (only when failed and we have a last_error)
        self.err_snippet = QLabel(""); self.err_snippet.setObjectName("cardErrSnippet")
        self.err_snippet.setWordWrap(True)
        self.err_snippet.setVisible(False)
        col.addWidget(self.err_snippet)

        self.status_row = QHBoxLayout()
        self.status_row.setSpacing(6)
        self.status_row.setContentsMargins(0, 3, 0, 0)
        col.addLayout(self.status_row)

        top.addLayout(col, 1)

        btns_widget = QWidget()
        btns_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btns = QHBoxLayout(btns_widget)
        btns.setSpacing(6); btns.setContentsMargins(0, 0, 0, 0)

        self.run_btn = QPushButton("▶  Run"); self.run_btn.setObjectName("btnRun")
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self._on_run_click)

        self.stop_btn = QPushButton("■  Stop"); self.stop_btn.setObjectName("btnStop")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.clicked.connect(lambda: self.stop_signal.emit(self.launch.id))

        self.logs_btn = QPushButton("☰  Logs"); self.logs_btn.setObjectName("btnLogs")
        self.logs_btn.setCursor(Qt.PointingHandCursor)
        self.logs_btn.clicked.connect(lambda: self.selected_signal.emit(self.launch.id))

        btns.addWidget(self.run_btn); btns.addWidget(self.stop_btn); btns.addWidget(self.logs_btn)
        top.addWidget(btns_widget, 0, Qt.AlignTop)

        outer.addWidget(top_widget)

        self.expand_container = QFrame()
        self.expand_container.setObjectName("expandContainer")
        self.expand_container.setVisible(False)
        ec = QVBoxLayout(self.expand_container)
        ec.setContentsMargins(0, 0, 0, 0)
        self.expandable_section = ExpandableSection(launch)
        ec.addWidget(self.expandable_section)
        outer.addWidget(self.expand_container)

        self.refresh()

    def _toggle_expand(self) -> None:
        is_open = self.expand_container.isVisible()
        new_open = not is_open
        self.expand_container.setVisible(new_open)
        self.expand_btn.setText("▾" if new_open else "▸")
        self.expand_btn.setProperty("open", "true" if new_open else "false")
        _restyle(self.expand_btn)
        self.setProperty("expanded", "true" if new_open else "false")
        _restyle(self)

    def _on_run_click(self) -> None:
        if self.launch.state == "running":
            self.restart_signal.emit(self.launch.id)
        else:
            self.run_signal.emit(self.launch.id)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        self.selected_signal.emit(self.launch.id)
        super().mousePressEvent(e)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        _restyle(self)

    def refresh(self) -> None:
        while self.status_row.count():
            item = self.status_row.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        # Star button
        self.star_btn.setText("⭐" if self.launch.starred else "☆")
        self.star_btn.setProperty("starred", "true" if self.launch.starred else "false")
        _restyle(self.star_btn)

        # Crash snippet visibility
        if self.launch.state == "failed" and self.launch.last_error:
            self.err_snippet.setText(self.launch.last_error)
            self.err_snippet.setVisible(True)
        else:
            self.err_snippet.setVisible(False)

        if self.launch.state == "running":
            self.status_row.addWidget(make_green_dot())
            self.status_row.addSpacing(2)
            r = QLabel("running"); r.setObjectName("statusRunning"); self.status_row.addWidget(r)
            s1 = QLabel("·"); s1.setObjectName("metaSep"); self.status_row.addWidget(s1)
            pid = QLabel(f"PID {self.launch.pid}"); pid.setObjectName("metaMono")
            self.status_row.addWidget(pid)
            s2 = QLabel("·"); s2.setObjectName("metaSep"); self.status_row.addWidget(s2)
            mm, ss = divmod(self.launch.uptime, 60)
            up = QLabel(f"{mm:02d}:{ss:02d}"); up.setObjectName("metaMono")
            self.status_row.addWidget(up)
            self.run_btn.setText("↻  Restart"); self.run_btn.setObjectName("btnRestart")
            self.run_btn.setEnabled(True); self.stop_btn.setEnabled(True)
            self.setProperty("running", "true"); self.setProperty("failed", "false")
        elif self.launch.state == "failed":
            self.status_row.addWidget(make_red_dot())
            self.status_row.addSpacing(2)
            f = QLabel("failed"); f.setObjectName("statusFailed"); self.status_row.addWidget(f)
            if self.launch.exit_code is not None:
                s1 = QLabel("·"); s1.setObjectName("metaSep"); self.status_row.addWidget(s1)
                ec = QLabel(f"exit {self.launch.exit_code}"); ec.setObjectName("metaMono")
                self.status_row.addWidget(ec)
            self.run_btn.setText("▶  Retry"); self.run_btn.setObjectName("btnRetry")
            self.run_btn.setEnabled(True); self.stop_btn.setEnabled(False)
            self.setProperty("running", "false"); self.setProperty("failed", "true")
        else:
            self.status_row.addWidget(make_grey_dot())
            self.status_row.addSpacing(2)
            s = QLabel("stopped"); s.setObjectName("statusStopped"); self.status_row.addWidget(s)
            self.run_btn.setText("▶  Run"); self.run_btn.setObjectName("btnRun")
            self.run_btn.setEnabled(True); self.stop_btn.setEnabled(False)
            self.setProperty("running", "false"); self.setProperty("failed", "false")

        self.status_row.addStretch()
        _restyle(self.run_btn)
        _restyle(self)


# ─── Toast (auto-dismissing notification) ───────────────────────────────────

class Toast(QFrame):
    dismissed = Signal()

    GLYPHS = {"ok": "▶", "err": "✕", "stop": "■", "info": "·"}
    _GLYPH_OBJ_NAME = {"ok": "toastGlyphOk", "err": "toastGlyphErr",
                       "stop": "toastGlyphStop", "info": "toastGlyphInfo"}

    def __init__(self, kind: str, title: str, subtitle: Optional[str] = None,
                 duration_ms: int = TOAST_DURATION_MS, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.setProperty("kind", kind)
        self.setCursor(Qt.PointingHandCursor)

        h = QHBoxLayout(self)
        h.setContentsMargins(12, 10, 12, 10)
        h.setSpacing(10)

        g = QLabel(self.GLYPHS.get(kind, "·"))
        g.setObjectName(self._GLYPH_OBJ_NAME.get(kind, "toastGlyphInfo"))
        h.addWidget(g)

        col = QVBoxLayout(); col.setSpacing(1); col.setContentsMargins(0, 0, 0, 0)
        t = QLabel(title); t.setObjectName("toastTitle"); t.setWordWrap(True)
        col.addWidget(t)
        if subtitle:
            s = QLabel(subtitle); s.setObjectName("toastSub"); s.setWordWrap(True)
            col.addWidget(s)
        h.addLayout(col, 1)

        x = QLabel("×"); x.setObjectName("toastX")
        h.addWidget(x)

        self.setMinimumWidth(280)
        self.setMaximumWidth(380)
        QTimer.singleShot(duration_ms, self.dismiss)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        self.dismiss()
        super().mousePressEvent(e)

    def dismiss(self) -> None:
        if self.parent() is not None:
            self.dismissed.emit()
            self.hide()
            self.deleteLater()


# ─── Command palette ────────────────────────────────────────────────────────

class CommandPalette(QDialog):
    triggered = Signal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("paletteRoot")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self._launches: List[Launch] = []
        self._items: List[dict] = []

        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(0)

        input_wrap = QFrame(); input_wrap.setObjectName("paletteInputWrap")
        ih = QHBoxLayout(input_wrap)
        ih.setContentsMargins(16, 14, 16, 14); ih.setSpacing(12)
        icon = QLabel("⌕"); icon.setObjectName("paletteIcon")
        ih.addWidget(icon)
        self.input = QLineEdit(); self.input.setObjectName("paletteInput")
        self.input.setPlaceholderText("Run a launch, search…")
        self.input.textChanged.connect(self._refilter)
        self.input.returnPressed.connect(self._activate_current)
        self.input.installEventFilter(self)
        ih.addWidget(self.input, 1)
        esc = QLabel("esc"); esc.setObjectName("paletteKbd")
        ih.addWidget(esc)
        v.addWidget(input_wrap)

        self.list = QListWidget(); self.list.setObjectName("paletteList")
        self.list.itemActivated.connect(lambda _i: self._activate_current())
        v.addWidget(self.list, 1)

        foot = QLabel("↑↓ navigate     ↵ select     esc close")
        foot.setObjectName("paletteFoot"); foot.setAlignment(Qt.AlignCenter)
        v.addWidget(foot)

        self.resize(PALETTE_WIDTH, PALETTE_HEIGHT)

    def open_with(self, launches: List[Launch]) -> None:
        self._launches = list(launches)
        self._items = self._build_items()
        self.input.clear()
        self._refilter("")
        p = self.parent()
        if isinstance(p, QWidget):
            pgeo = p.geometry()
            x = pgeo.x() + (pgeo.width() - self.width()) // 2
            y = pgeo.y() + 120
            self.move(x, y)
        self.show()
        self.raise_()
        self.input.setFocus()

    def _build_items(self) -> List[dict]:
        items: List[dict] = []
        running = [l for l in self._launches if l.state == "running"]
        if running:
            items.append({"kind": "action", "action_id": "stop-all", "glyph": "■",
                          "title": f"Stop all running ({len(running)})", "subtitle": ""})
        items.append({"kind": "action", "action_id": "clear-logs", "glyph": "✕",
                      "title": "Clear logs", "subtitle": ""})
        for l in self._launches:
            verb = "Retry" if l.state == "failed" else "Run"
            items.append({"kind": "run", "launch_id": l.id, "glyph": "▶",
                          "title": f"{verb}  {l.pkg} / {l.name}",
                          "subtitle": l.desc,
                          "disabled": l.state == "running"})
            if l.state == "running":
                items.append({"kind": "stop", "launch_id": l.id, "glyph": "■",
                              "title": f"Stop  {l.pkg} / {l.name}",
                              "subtitle": f"PID {l.pid}"})
        return items

    def _refilter(self, q: str) -> None:
        q = (q or "").strip().lower()
        self.list.clear()
        for it in self._items:
            haystack = f"{it['title']} {it.get('subtitle', '')}".lower()
            if q and q not in haystack:
                continue
            text = f"{it['glyph']}   {it['title']}"
            if it.get("subtitle"):
                text += f"   ·   {it['subtitle']}"
            row = QListWidgetItem(text); row.setData(Qt.UserRole, it)
            if it.get("disabled"):
                row.setFlags(row.flags() & ~Qt.ItemIsEnabled)
            self.list.addItem(row)
        for i in range(self.list.count()):
            if self.list.item(i).flags() & Qt.ItemIsEnabled:
                self.list.setCurrentRow(i)
                break

    def _activate_current(self) -> None:
        item = self.list.currentItem()
        if not item or not (item.flags() & Qt.ItemIsEnabled):
            return
        data = item.data(Qt.UserRole)
        if data:
            self.triggered.emit(data)
            self.close()

    def keyPressEvent(self, e) -> None:
        if e.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(e)

    def eventFilter(self, obj, ev):
        if obj is self.input and ev.type() == QEvent.Type.KeyPress:
            k = ev.key()
            if k == Qt.Key_Down:
                self.list.setCurrentRow(min(self.list.currentRow() + 1, self.list.count() - 1))
                return True
            if k == Qt.Key_Up:
                self.list.setCurrentRow(max(self.list.currentRow() - 1, 0))
                return True
            if k == Qt.Key_Escape:
                self.close()
                return True
        return super().eventFilter(obj, ev)


# ─── Logs panel (with level filters + search + follow/wrap) ─────────────────

class LogsPanel(QFrame):
    clear_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("logsPanel")
        self.setMaximumHeight(LOGS_PANEL_MAX_HEIGHT)
        self._launch: Optional[Launch] = None
        self._level_filter = "ALL"
        self._search_query = ""
        self._follow = True
        self._wrap = True

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 12, 24, 16); v.setSpacing(8)

        head = QHBoxLayout(); head.setSpacing(8)

        key = QLabel("LOGS"); key.setObjectName("logsKey")
        set_letter_spacing(key, 1.4); head.addWidget(key)
        sep = QLabel("·"); sep.setObjectName("logsSep"); head.addWidget(sep)
        self.subject_label = QLabel("—"); self.subject_label.setObjectName("logsSubject")
        head.addWidget(self.subject_label)
        self.live_pill = self._build_live_pill()
        head.addWidget(self.live_pill)
        head.addStretch()

        self.level_buttons: Dict[str, QPushButton] = {}
        for lvl in LOG_LEVELS:
            b = QPushButton(lvl)
            b.setProperty("logLevel", lvl)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setChecked(lvl == "ALL")
            b.clicked.connect(lambda _ck, lv=lvl: self._set_level(lv))
            self.level_buttons[lvl] = b
            head.addWidget(b)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("logSearch")
        self.search_input.setPlaceholderText("Search…")
        self.search_input.textChanged.connect(self._on_search_changed)
        head.addWidget(self.search_input)

        self.follow_btn = QPushButton("✓ Follow"); self.follow_btn.setObjectName("btnGhost")
        self.follow_btn.setCheckable(True); self.follow_btn.setChecked(True)
        self.follow_btn.setCursor(Qt.PointingHandCursor)
        self.follow_btn.clicked.connect(self._toggle_follow)
        head.addWidget(self.follow_btn)

        self.wrap_btn = QPushButton("✓ Wrap"); self.wrap_btn.setObjectName("btnGhost")
        self.wrap_btn.setCheckable(True); self.wrap_btn.setChecked(True)
        self.wrap_btn.setCursor(Qt.PointingHandCursor)
        self.wrap_btn.clicked.connect(self._toggle_wrap)
        head.addWidget(self.wrap_btn)

        clear_btn = QPushButton("Clear"); clear_btn.setObjectName("btnGhost")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(lambda: self.clear_requested.emit())
        head.addWidget(clear_btn)

        v.addLayout(head)

        self.body = QTextEdit(); self.body.setObjectName("logsBody")
        self.body.setReadOnly(True)
        self.body.setLineWrapMode(QTextEdit.WidgetWidth)
        v.addWidget(self.body, 1)

    def _build_live_pill(self) -> QFrame:
        f = QFrame(); f.setObjectName("logsLive")
        h = QHBoxLayout(f); h.setContentsMargins(8, 2, 10, 2); h.setSpacing(5)
        h.addWidget(make_green_dot())
        lbl = QLabel("LIVE"); lbl.setObjectName("logsLiveText")
        set_letter_spacing(lbl, 1.0); h.addWidget(lbl)
        f.setVisible(False)
        return f

    def set_launch(self, launch: Optional[Launch]) -> None:
        self._launch = launch
        if launch:
            self.subject_label.setText(f"{launch.pkg} / {launch.name}")
            self.live_pill.setVisible(launch.state == "running")
        else:
            self.subject_label.setText("—")
            self.live_pill.setVisible(False)
        self._render_all()

    def refresh_live_pill(self) -> None:
        """Called when the selected launch's state changes (running/stopped/failed)."""
        if self._launch:
            self.live_pill.setVisible(self._launch.state == "running")

    def _update_counts(self) -> None:
        counts = {lvl: 0 for lvl in LOG_LEVELS}
        if self._launch:
            for entry in self._launch.logs:
                counts["ALL"] += 1
                if entry.level in counts:
                    counts[entry.level] += 1
        for lvl, btn in self.level_buttons.items():
            btn.setText(f"{lvl} {counts[lvl]}")

    def _matches_filter(self, entry: LogEntry) -> bool:
        if self._level_filter != "ALL" and entry.level != self._level_filter:
            return False
        q = self._search_query
        if q and q not in entry.msg.lower() and q not in entry.node.lower():
            return False
        return True

    def _render_all(self) -> None:
        self.body.clear()
        self._update_counts()
        if not self._launch:
            return
        for entry in self._launch.logs:
            if self._matches_filter(entry):
                self._append_entry_html(entry)
        if self._follow:
            sb = self.body.verticalScrollBar()
            sb.setValue(sb.maximum())

    def append_entry(self, entry: LogEntry) -> None:
        """Append a single live entry (called by the backend on every new line)."""
        if not self._launch:
            return
        self._update_counts()
        if not self._matches_filter(entry):
            return
        self._append_entry_html(entry)
        if self._follow:
            sb = self.body.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _append_entry_html(self, entry: LogEntry) -> None:
        lvl_color = LOG_LEVEL_COLORS.get(entry.level, "#56d364")
        msg = entry.msg.replace("<", "&lt;").replace(">", "&gt;")
        html = (
            f'<span style="color:#6e7681;">{entry.fmt_time()}</span> '
            f'<span style="color:{lvl_color};">[{entry.level:5s}]</span> '
            f'<span style="color:#79c0ff;">[{entry.node}]</span>'
            f'<span style="color:#c9d1d9;">: {msg}</span>'
        )
        self.body.append(html)

    def _set_level(self, lvl: str) -> None:
        self._level_filter = lvl
        for k, btn in self.level_buttons.items():
            btn.setChecked(k == lvl)
        self._render_all()

    def _on_search_changed(self, text: str) -> None:
        self._search_query = text.strip().lower()
        self._render_all()

    def _toggle_follow(self) -> None:
        self._follow = self.follow_btn.isChecked()
        self.follow_btn.setText(("✓ " if self._follow else "") + "Follow")

    def _toggle_wrap(self) -> None:
        self._wrap = self.wrap_btn.isChecked()
        self.body.setLineWrapMode(QTextEdit.WidgetWidth if self._wrap else QTextEdit.NoWrap)
        self.wrap_btn.setText(("✓ " if self._wrap else "") + "Wrap")


# ─── Embedded WebEngine page ────────────────────────────────────────────────

class WebEnginePage(QWidget):
    """Lazy-loaded WebEngine page for a local HTML asset."""

    def __init__(self, html_path: Path) -> None:
        super().__init__()
        self.setObjectName("root")
        self._html_path = html_path
        self._initialized = False
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        if not _WEBENGINE_AVAILABLE:
            self._show_missing("PySide6 WebEngine is not installed.")
            return
        if not self._html_path.exists():
            self._show_missing(f"Asset not found:\n{self._html_path}")
            return
        view = QWebEngineView()
        # Allow file:// pages to load React/Babel/roslib from CDN.
        view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
        )
        view.setUrl(QUrl.fromLocalFile(str(self._html_path)))
        self._layout.addWidget(view)

    def _show_missing(self, reason: str) -> None:
        msg = QLabel(
            f"{reason}\n\n"
            "To enable this tab, install the Qt WebEngine module:\n\n"
            "    pip install PySide6-Addons\n\n"
            "Then restart the launch manager."
        )
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet("color: #6e7681; font-size: 13px; padding: 48px;")
        msg.setWordWrap(True)
        self._layout.addWidget(msg)
