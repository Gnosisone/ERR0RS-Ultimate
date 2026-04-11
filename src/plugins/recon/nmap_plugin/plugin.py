# plugins/recon/nmap_plugin/plugin.py
import subprocess
from src.core.plugin_base import BasePlugin


class Plugin(BasePlugin):

    SCAN_PROFILES = {
        "scan":     ["-sV", "-T4"],
        "portscan": ["-p-", "-T4", "--open"],
        "stealth":  ["-sS", "-T2", "-f"],
        "udp":      ["-sU", "--top-ports", "200"],
        "vuln":     ["-sV", "--script=vuln"],
        "full":     ["-A", "-T4", "-p-"],
    }

    def validate_args(self, args: dict) -> bool:
        return bool(
            args.get("target") or (
                hasattr(self.context, "get_active_target")
                and self.context.get_active_target()
            )
        )

    def run(self, command: str, args: dict):
        target = args.get("target") or (
            self.context.get_active_target()
            if hasattr(self.context, "get_active_target") else None
        )
        if not target:
            return "[nmap] Error: No target specified"

        flags = self.SCAN_PROFILES.get(command, ["-sV"])
        extra = args.get("flags", [])
        if isinstance(extra, str):
            extra = extra.split()

        cmd = ["nmap"] + flags + extra + [target]
        self.log(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=args.get("timeout", 300)
            )
            output = result.stdout or result.stderr

            if hasattr(self.context, "add_finding"):
                self.context.add_finding({
                    "plugin": "nmap", "type": command,
                    "target": target, "command": " ".join(cmd),
                    "output": output,
                })

            self.emit("scan.complete", {"target": target, "command": command})
            return output

        except subprocess.TimeoutExpired:
            return f"[nmap] Timed out after {args.get('timeout', 300)}s"
        except FileNotFoundError:
            return "[nmap] Error: nmap not found — run: apt install nmap"
        except Exception as e:
            self.log(f"Error: {e}", level="error")
            return f"[nmap] Error: {e}"
