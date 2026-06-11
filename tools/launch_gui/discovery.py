"""Launch discovery: walk `src/*/launch/`, parse docs + args."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List, Optional

from .meta import LAUNCH_META
from .model import Launch, instantiate_args


def _extract_doc(path: Path, fmt: str) -> Optional[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if fmt == "py":
        try:
            doc = ast.get_docstring(ast.parse(text))
        except SyntaxError:
            doc = None
        if doc:
            return doc.strip().split("\n", 1)[0].rstrip(".")
    else:
        for m in re.finditer(r"<!--\s*(.+?)\s*-->", text, re.DOTALL):
            line = m.group(1).strip().split("\n", 1)[0].strip()
            line = line.strip(" =-*#").strip()
            if line:
                return line
    return None


def _infer_kind(default_str: str) -> str:
    d = default_str.lower()
    if d in ("true", "false"):
        return "bool"
    if d.replace(".", "").replace("-", "").isdigit():
        return "number"
    return "string"


def parse_declare_launch_argument(text: str) -> List[dict]:
    """Walk a `.launch.py` AST and extract `DeclareLaunchArgument` calls.

    Returns a list of {key, default, kind, options?, help?}. The `value` slot
    is added later by `instantiate_args`.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    args: List[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # Match DeclareLaunchArgument(...) or anything.DeclareLaunchArgument(...)
        if isinstance(node.func, ast.Name):
            if node.func.id != "DeclareLaunchArgument":
                continue
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr != "DeclareLaunchArgument":
                continue
        else:
            continue

        spec: dict = {}
        # Positional: DeclareLaunchArgument("name", ...)
        if node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                spec["key"] = first.value

        for kw in node.keywords:
            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                spec["key"] = kw.value.value
            elif kw.arg == "default_value" and isinstance(kw.value, ast.Constant):
                spec["default"] = str(kw.value.value)
            elif kw.arg == "description" and isinstance(kw.value, ast.Constant):
                spec["help"] = kw.value.value
            elif kw.arg == "choices" and isinstance(kw.value, (ast.List, ast.Tuple)):
                opts = [str(el.value) for el in kw.value.elts
                        if isinstance(el, ast.Constant)]
                if opts:
                    spec["options"] = opts
                    spec["kind"] = "enum"

        if "key" not in spec:
            continue
        spec.setdefault("default", "")
        spec.setdefault("kind", _infer_kind(spec["default"]))
        args.append(spec)
    return args


def parse_xml_args(text: str) -> List[dict]:
    """Extract `<arg name=... default=... description=...>` from a .launch.xml."""
    out: List[dict] = []
    pattern = re.compile(
        r'<arg\s+name="([^"]+)"'
        r'(?:\s+default="([^"]*)")?'
        r'(?:\s+description="([^"]*)")?',
    )
    for m in pattern.finditer(text):
        name = m.group(1)
        default = m.group(2) or ""
        desc = m.group(3) or ""
        spec: dict = {"key": name, "default": default, "kind": _infer_kind(default)}
        if desc:
            spec["help"] = desc
        out.append(spec)
    return out


def _autodiscover_args(path: Path, fmt: str) -> List[dict]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return parse_declare_launch_argument(text) if fmt == "py" else parse_xml_args(text)


def discover_launches(workspace: Path) -> List[Launch]:
    """Scan `<workspace>/src/*/launch/*.launch.{py,xml}` and produce Launches.

    For each file:
      - description: curated `LAUNCH_META[key]['description']` first, then the
        Python module docstring or first XML comment.
      - args: curated meta `args:` first, then autodiscovered from AST/regex.
      - tags / phase / starred / presets: only from meta.
    """
    src = workspace / "src"
    out: List[Launch] = []
    if not src.is_dir():
        return out

    for pkg_dir in sorted(src.iterdir()):
        if not pkg_dir.is_dir():
            continue
        launch_dir = pkg_dir / "launch"
        if not launch_dir.is_dir():
            continue
        pkg = pkg_dir.name
        for f in sorted(launch_dir.iterdir()):
            stem = f.name
            if stem.endswith(".launch.py"):
                fmt, name = "py", stem[: -len(".launch.py")]
            elif stem.endswith(".launch.xml"):
                fmt, name = "xml", stem[: -len(".launch.xml")]
            else:
                continue
            key = f"{pkg}/{name}"
            meta = LAUNCH_META.get(key, {})
            desc = meta.get("description") or _extract_doc(f, fmt) or "(no description)"
            arg_spec = list(meta["args"]) if meta.get("args") else _autodiscover_args(f, fmt)
            out.append(Launch(
                id=f"{pkg}__{name}",
                pkg=pkg, name=name, desc=desc,
                tags=list(meta.get("tags", [])),
                phase=meta.get("phase", ""),
                starred=bool(meta.get("starred", False)),
                file_path=f, file_format=fmt,
                args=instantiate_args(arg_spec),
                presets=list(meta.get("presets", [])),
            ))
    # Starred first, then alphabetical by pkg/name.
    out.sort(key=lambda l: (not l.starred, l.pkg, l.name))
    return out
