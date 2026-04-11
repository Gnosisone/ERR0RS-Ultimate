# core/plugin_manager.py
# ERR0RS-Ultimate Plugin Manager
# Discovers, loads, indexes, and executes plugins

import importlib.util
import os
import json
import logging

logger = logging.getLogger("PluginManager")


class PluginManager:
    def __init__(self, plugin_dir="plugins", context=None):
        self.plugin_dir    = plugin_dir
        self.context       = context or {}
        self.plugins       = {}          # name → {instance, manifest}
        self.command_index = {}          # command → plugin_name (O(1) lookup)

    # ── Discovery & loading ──────────────────────────────────────

    def load_plugins(self):
        for root, dirs, files in os.walk(self.plugin_dir):
            if "manifest.json" not in files:
                continue
            self._load_one(root)

    def _load_one(self, root: str):
        manifest_path = os.path.join(root, "manifest.json")
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)

            self._validate_manifest(manifest)

            plugin_path = os.path.join(root, manifest["entry_point"])
            if not os.path.exists(plugin_path):
                logger.warning(f"Entry point missing: {plugin_path}")
                return

            spec   = importlib.util.spec_from_file_location(manifest["name"], plugin_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, "Plugin"):
                logger.warning(f"No Plugin class in {plugin_path}")
                return

            instance          = module.Plugin(context=self.context)
            instance.manifest = manifest
            instance.on_load()

            self.plugins[manifest["name"]] = {
                "instance": instance,
                "manifest": manifest,
            }

            for cmd in manifest.get("commands", []):
                if cmd in self.command_index:
                    logger.warning(
                        f"Command conflict: '{cmd}' already claimed by "
                        f"'{self.command_index[cmd]}' — skipping"
                    )
                else:
                    self.command_index[cmd] = manifest["name"]

            logger.info(f"Loaded: {manifest['name']} v{manifest.get('version','?')}")

        except Exception as e:
            logger.error(f"Failed to load plugin at {root}: {e}")

    # ── Execution ────────────────────────────────────────────────

    def execute(self, command: str, args: dict):
        plugin_name = self.command_index.get(command)

        if not plugin_name:
            return f"[ERR0RS] No plugin found for command: '{command}'"

        entry    = self.plugins[plugin_name]
        instance = entry["instance"]
        manifest = entry["manifest"]

        # Permission gate
        required = manifest.get("permissions", [])
        if hasattr(self.context, "has_permission"):
            for perm in required:
                if not self.context.has_permission(perm):
                    return f"[ERR0RS] Permission denied: '{perm}' required by '{plugin_name}'"

        if not instance.enabled:
            return f"[ERR0RS] Plugin '{plugin_name}' is disabled."

        try:
            if not instance.validate_args(args):
                return f"[ERR0RS] Invalid args for command '{command}'"
            result = instance.run(command, args)
            # log to shared context history
            if hasattr(self.context, "log_action"):
                self.context.log_action(plugin_name, command, args, result)
            return result
        except Exception as e:
            logger.error(f"Plugin '{plugin_name}' crashed on '{command}': {e}")
            return f"[ERR0RS] Plugin error: {e}"

    # ── Hot-swap ─────────────────────────────────────────────────

    def unload_plugin(self, name: str):
        if name in self.plugins:
            self.plugins[name]["instance"].on_unload()
            del self.plugins[name]
            self.command_index = {
                cmd: pname
                for cmd, pname in self.command_index.items()
                if pname != name
            }
            logger.info(f"Unloaded: {name}")

    def reload_plugin(self, name: str):
        if name in self.plugins:
            root = os.path.dirname(
                os.path.join(self.plugin_dir,
                             self.plugins[name]["manifest"]["entry_point"])
            )
            self.unload_plugin(name)
            self._load_one(root)

    # ── Introspection ────────────────────────────────────────────

    def list_plugins(self):
        return [
            {
                "name":     name,
                "version":  data["manifest"].get("version"),
                "category": data["manifest"].get("category"),
                "commands": data["manifest"].get("commands", []),
                "enabled":  data["instance"].enabled,
            }
            for name, data in self.plugins.items()
        ]

    def get_available_commands(self):
        return {
            name: data["manifest"].get("commands", [])
            for name, data in self.plugins.items()
        }

    # ── Validation ───────────────────────────────────────────────

    def _validate_manifest(self, manifest: dict):
        for field in ["name", "entry_point", "commands"]:
            if field not in manifest:
                raise ValueError(f"Manifest missing required field: '{field}'")
