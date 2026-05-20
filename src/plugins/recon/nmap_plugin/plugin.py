# plugins/recon/nmap_plugin/plugin.py
# ERR0RS-Ultimate — Nmap Recon Plugin

from src.core.plugin_base import BasePlugin


class Plugin(BasePlugin):

    # NOTE: every profile carries -v so nmap emits live progress
    # ("Discovered open port ...", "Scanning ...") instead of staying
    # silent until the final report — this is what makes the CLI/dashboard
    # stream feel interactive.  Long scans also get --stats-every so a
    # progress line appears even while nmap is grinding.
    SCAN_PROFILES = {
        "scan":     ["-sV", "-T4", "-v"],
        "portscan": ["-p-", "-T4", "--open", "-v", "--stats-every", "5s"],
        "stealth":  ["-sS", "-T2", "-f", "-v"],
        "udp":      ["-sU", "--top-ports", "200", "-v", "--stats-every", "5s"],
        "vuln":     ["-sV", "--script=vuln", "-v", "--stats-every", "10s"],
        "full":     ["-A", "-T4", "-p-", "-v", "--stats-every", "10s"],
    }

    def validate_args(self, args: dict) -> bool:
        return bool(args.get("target"))

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

        # stream() runs nmap line-buffered and publishes every stdout
        # line as a tool.output event — the CLI and dashboard render it
        # live.  Returns a PluginResult once the scan completes.
        result = self.stream(
            cmd,
            tool_name="nmap",
            timeout=args.get("timeout", 300),
            target=target,
        )

        output = result.output
        meta   = result.metadata or {}

        if meta.get("status") == "timeout":
            return f"[nmap] Scan timed out after {args.get('timeout', 300)}s"
        if meta.get("status") == "failed" and not output:
            return f"[nmap] Error: {meta.get('stderr') or 'scan failed'}"

        # Push finding to shared context
        self.context.add_finding({
            "plugin":  "nmap",
            "type":    command,
            "target":  target,
            "command": " ".join(cmd),
            "output":  output,
        })

        self.emit("scan.complete", {"target": target, "command": command})
        return output

    def info(self):
        return {
            "name":        "nmap_plugin",
            "description": "Network scanner — recon, port scan, stealth, vuln detection",
            "profiles":    list(self.SCAN_PROFILES.keys()),
        }
