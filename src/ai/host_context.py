"""
ERR0RS ULTIMATE — Host Context Helpers
═══════════════════════════════════════════════════════════════════

Detects the host's network identity (LAN IP, interface name, hostname)
so demos, payloads, and listener commands can be auto-filled with the
user's actual address instead of placeholder text.

WHY THIS EXISTS:
  Before this module, every demo and BadUSB payload had to be hand-
  edited by the user to substitute their IP. That breaks the "real
  working artifact" promise for OPERATE tier and frustrates LEARN tier
  students who don't yet know how to find their own IP. Auto-fill is
  the single highest-leverage UX improvement we can make to demo mode
  and Payload Studio.

WHAT IT DOES NOT DO:
  - Does NOT detect the user's PUBLIC IP. Public IP discovery requires
    an outbound network call (e.g. to ipify.org or icanhazip.com),
    which violates the offline-first principle. If a user needs their
    public IP for a payload, they invoke that workflow explicitly.
  - Does NOT auto-pick a target. The user always provides targets.
    This module supplies the SOURCE side only — the user's own address.
  - Does NOT cache. Network interfaces change (laptop docking, VPN
    connect/disconnect). Every call queries fresh.

USAGE:
    from src.ai.host_context import (
        get_lan_ip, get_interface_addrs, get_default_route_iface,
        substitute_placeholders, HostContext
    )

    # Quick: just give me a usable LAN IP
    ip = get_lan_ip()                # → '192.168.1.50' or None
    ip = get_lan_ip(prefer='wlan0')  # → IP of wlan0 if present

    # Detailed: what interfaces does this host have?
    addrs = get_interface_addrs()    # → {'wlan0': '192.168.1.50', ...}

    # Template substitution for payloads + demo commands
    cmd = substitute_placeholders(
        'nmap -sV {USER_IP}',
        extra={'PORT': '4444'},
    )
    # → 'nmap -sV 192.168.1.50'

    # Rich snapshot for the UI/preflight
    ctx = HostContext.snapshot()
    print(ctx.summary())
"""
from __future__ import annotations

import logging
import re
import socket
import subprocess
from dataclasses import dataclass, field, asdict
from typing import Optional

log = logging.getLogger(__name__)

# Common placeholder names users will encounter in payload templates
# or demo recipes. We support multiple synonyms because different
# tool ecosystems use different conventions.
PLACEHOLDER_KEYS_LAN_IP = (
    "USER_IP", "LHOST", "USERS_IP", "MY_IP",
    "LAN_IP", "HOST_IP", "SOURCE_IP", "ATTACKER_IP",
)


# ── Low-level interface enumeration ──────────────────────────────────────

def _list_ipv4_addrs_via_socket() -> dict[str, str]:
    """Fallback: use a UDP-connect-no-send trick to learn the LAN IP
    the kernel would use for an arbitrary outbound destination. Doesn't
    give us per-interface info but works on every platform.

    The trick: socket.connect on UDP doesn't send anything but does
    select a route, after which getsockname() returns the local addr."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # 10.255.255.255 is a non-routable RFC1918 address that
            # forces route selection without ever reaching anywhere
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
            return {"_default": ip} if ip and ip != "0.0.0.0" else {}
        finally:
            s.close()
    except Exception:
        return {}


def _list_ipv4_addrs_via_ip_cmd() -> dict[str, str]:
    """Use `ip -4 addr` (modern Linux). Returns {iface: ip} for every
    IPv4-bound interface that isn't loopback."""
    try:
        proc = subprocess.run(
            ["ip", "-4", "-o", "addr", "show"],
            capture_output=True, text=True, timeout=3,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return {}
    if proc.returncode != 0:
        return {}

    out: dict[str, str] = {}
    # Lines look like: "3: wlan0    inet 192.168.1.50/24 brd ..."
    pat = re.compile(r"^\d+:\s+(\S+)\s+inet\s+(\d+\.\d+\.\d+\.\d+)/")
    for line in proc.stdout.splitlines():
        m = pat.match(line)
        if not m:
            continue
        iface, ip = m.group(1), m.group(2)
        if iface == "lo":
            continue   # skip loopback
        out[iface] = ip
    return out


def get_interface_addrs() -> dict[str, str]:
    """Return {iface_name: ipv4_address} for all non-loopback IPv4
    interfaces. Empty dict if detection fails or host has no LAN."""
    addrs = _list_ipv4_addrs_via_ip_cmd()
    if addrs:
        return addrs
    # Fallback to socket trick — returns under '_default' key
    return _list_ipv4_addrs_via_socket()


def get_default_route_iface() -> Optional[str]:
    """Return the name of the interface used for the default route, or
    None. Used as the 'most likely correct' choice when the user
    didn't specify an interface."""
    try:
        proc = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True, timeout=3,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    # "default via 192.168.1.1 dev wlan0 proto dhcp ..."
    m = re.search(r"\bdev\s+(\S+)", proc.stdout)
    return m.group(1) if m else None


def get_lan_ip(prefer: Optional[str] = None) -> Optional[str]:
    """Return the host's LAN IPv4 address as a string.

    Selection order:
      1. If `prefer` is given and that interface has an address, return it
      2. Otherwise, prefer the interface carrying the default route
      3. Otherwise, return the first non-loopback IPv4 found
      4. If all else fails, the UDP-connect fallback
      5. None if even that fails (host has no network)
    """
    addrs = get_interface_addrs()
    if prefer and prefer in addrs:
        return addrs[prefer]

    default_iface = get_default_route_iface()
    if default_iface and default_iface in addrs:
        return addrs[default_iface]

    # First non-loopback we find
    for iface, ip in addrs.items():
        if iface != "_default":
            return ip
    # Socket fallback
    if "_default" in addrs:
        return addrs["_default"]
    return None


def get_hostname() -> str:
    """Return the host's name (best-effort, never raises)."""
    try:
        return socket.gethostname() or "localhost"
    except Exception:
        return "localhost"


# ── Placeholder substitution ─────────────────────────────────────────────

def substitute_placeholders(
    template: str,
    extra: Optional[dict] = None,
    user_ip: Optional[str] = None,
) -> str:
    """Fill {PLACEHOLDER} tokens in a template string.

    Placeholders supported:
      {USER_IP}, {LHOST}, {USERS_IP}, {MY_IP}, {LAN_IP},
      {HOST_IP}, {SOURCE_IP}, {ATTACKER_IP}     → host's LAN IP
      {HOSTNAME}                                → socket.gethostname()

    Plus anything in `extra` (e.g. {PORT}, {TARGET}).

    Tokens that can't be resolved are left in place — easier to debug
    than silent removal. The recipe author OR the user (in OPERATE
    tier) is responsible for ensuring critical placeholders resolve.

    Args:
        template: the string with {TOKEN} placeholders
        extra:    additional key→value substitutions (e.g. {'PORT': '4444'})
        user_ip:  override the detected LAN IP (for tests or manual specify)
    """
    ip = user_ip or get_lan_ip()
    subs: dict[str, str] = {}
    if ip is not None:
        for k in PLACEHOLDER_KEYS_LAN_IP:
            subs[k] = ip
    subs["HOSTNAME"] = get_hostname()
    if extra:
        subs.update({k: str(v) for k, v in extra.items()})

    def _repl(m: re.Match) -> str:
        key = m.group(1)
        return subs.get(key, m.group(0))  # leave unresolved as-is

    return re.sub(r"\{([A-Z_]+)\}", _repl, template)


# ── Rich snapshot for UI / preflight ─────────────────────────────────────

@dataclass
class HostContext:
    hostname:        str
    lan_ip:          Optional[str]
    default_iface:   Optional[str]
    all_interfaces:  dict = field(default_factory=dict)

    @classmethod
    def snapshot(cls) -> "HostContext":
        return cls(
            hostname=get_hostname(),
            lan_ip=get_lan_ip(),
            default_iface=get_default_route_iface(),
            all_interfaces=get_interface_addrs(),
        )

    def summary(self) -> str:
        """Single-line human summary, useful for preflight prints."""
        if not self.lan_ip:
            return f"Host: {self.hostname} (no LAN address detected)"
        iface_note = f" on {self.default_iface}" if self.default_iface else ""
        return f"Host: {self.hostname} @ {self.lan_ip}{iface_note}"

    def to_dict(self) -> dict:
        return asdict(self)
