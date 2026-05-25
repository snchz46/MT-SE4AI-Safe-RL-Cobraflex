"""CobraFlex Launch Manager — split into:

    constants    magic numbers, palette / phase colors
    model        Launch + LogEntry dataclasses, build_command, args helpers
    meta         LAUNCH_META (curated metadata, YAML override)
    discovery    walk src/*/launch/, AST-parse DeclareLaunchArgument
    backend      Backend / MockBackend / RosBackend (QProcess + setsid)
    widgets      LaunchCard, ArgRow, ExpandableSection, LogsPanel, Toast,
                 CommandPalette, WebEnginePage, helpers
    app          LaunchGui main window, main() entrypoint
    style.qss    All Qt Style Sheets (loaded at startup)
"""

from .app import main

__version__ = "0.2.0"
__all__ = ["main", "__version__"]
