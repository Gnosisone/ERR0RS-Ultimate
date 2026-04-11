# src/core/plugin_base.py
# ERR0RS-Ultimate Base Plugin Class

class BasePlugin:
    def __init__(self, context):
        self.context  = context
        self.manifest = {}
        self.enabled  = True

    def run(self, command, args):
        raise NotImplementedError("Plugin must implement run()")

    def validate_args(self, args) -> bool:
        return True

    def on_load(self):
        pass

    def on_unload(self):
        pass

    def emit(self, event: str, data=None):
        if hasattr(self.context, "event_bus"):
            self.context.event_bus.emit(event, data)

    def log(self, msg: str, level: str = "info"):
        if hasattr(self.context, "logger"):
            getattr(self.context.logger, level)(
                f"[{self.info()['name']}] {msg}"
            )

    def info(self) -> dict:
        return {
            "name":        self.__class__.__name__,
            "description": self.manifest.get("description", "No description"),
            "version":     self.manifest.get("version", "unknown"),
            "category":    self.manifest.get("category", "misc"),
            "commands":    self.manifest.get("commands", []),
        }
