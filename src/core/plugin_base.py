# core/plugin_base.py
# ERR0RS-Ultimate Base Plugin Class
# All plugins inherit from this

class BasePlugin:
    def __init__(self, context):
        self.context = context   # SharedContext instance
        self.manifest = {}       # populated by PluginManager at load
        self.enabled = True

    # ── Required override ────────────────────────────────────────

    def run(self, command, args):
        raise NotImplementedError("Plugin must implement run()")

    # ── Optional overrides ───────────────────────────────────────

    def validate_args(self, args) -> bool:
        """Override to validate args before run() is called."""
        return True

    def on_load(self):
        """Called once when plugin is registered. Set up connections here."""
        pass

    def on_unload(self):
        """Called on hot-swap or shutdown. Close sockets, serial ports, etc."""
        pass

    # ── Helpers available to all plugins ─────────────────────────

    def emit(self, event: str, data=None):
        """Push an event to the core event bus."""
        if hasattr(self.context, "event_bus"):
            self.context.event_bus.emit(event, data)

    def log(self, msg: str, level: str = "info"):
        """Route log messages through the shared logger."""
        if hasattr(self.context, "logger"):
            getattr(self.context.logger, level)(
                f"[{self.info()['name']}] {msg}"
            )

    def info(self) -> dict:
        return {
            "name":        self.__class__.__name__,
            "description": self.manifest.get("description", "No description provided"),
            "version":     self.manifest.get("version", "unknown"),
            "category":    self.manifest.get("category", "misc"),
            "commands":    self.manifest.get("commands", []),
        }
