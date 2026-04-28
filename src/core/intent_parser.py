"""
ERR0RS Intent Parser — Hybrid
═════════════════════════════
Fast path: regex rules for 90% of commands.
Slow path: local Ollama for natural language ambiguity.

Returned intent schema:
{
  "action":  "run_tool"|"set_target"|"set_mode"|"start_auto"|"pause"|
             "resume"|"status"|"teach"|"ask_user"|"chat",
  "tool":    str | None,
  "args":    list[str],
  "target":  str | None,
  "mode":    str | None,
  "goal":    str | None,
  "topic":   str | None,
  "question": str | None,
  "question_key": str | None,
  "reason":  str | None,
  "confidence": float,
}
"""
import re, json, logging, subprocess
log = logging.getLogger("err0rs.intent")


TARGET_PATTERN = re.compile(
    r"\b("
    r"(?:(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?)"
    r"|https?://[^\s]+"
    r"|(?:[a-z0-9-]+\.)+[a-z]{2,}(?::\d+)?"
    r"|localhost(?::\d+)?"
    r")\b",
    re.IGNORECASE,
)

TOOL_ALIASES = {
    "nmap":        ["nmap","port scan","port-scan","scan ports"],
    "masscan":     ["masscan","mass scan"],
    "nikto":       ["nikto"],
    "gobuster":    ["gobuster","dir brute","directory brute","dirb"],
    "ffuf":        ["ffuf","fuzz"],
    "sqlmap":      ["sqlmap","sql injection","sqli"],
    "hydra":       ["hydra","brute force","password spray"],
    "nuclei":      ["nuclei","template scan"],
    "metasploit":  ["metasploit","msfconsole","msf"],
    "whatweb":     ["whatweb","fingerprint"],
    "wpscan":      ["wpscan","wordpress scan"],
    "dalfox":      ["dalfox","xss fuzz","xss scan"],
    "enum4linux":  ["enum4linux","smb enum"],
    "crackmapexec":["crackmapexec","cme"],
    "aircrack":    ["aircrack","aircrack-ng"],
    "hashcat":     ["hashcat","crack hash","hash crack"],
    "subfinder":   ["subfinder","subdomain enum"],
}


NMAP_SCAN_FLAGS = {
    "syn":       "-sS",
    "stealth":   "-sS",
    "tcp":       "-sT",
    "connect":   "-sT",
    "udp":       "-sU",
    "ping":      "-sn",
    "no ping":   "-Pn",
    "no-ping":   "-Pn",
    "aggressive":"-A",
    "version":   "-sV",
    "os":        "-O",
    "fast":      "-F",
    "full":      "-p-",
    "all ports": "-p-",
    "top 1000":  "--top-ports 1000",
}

CONTROL_PATTERNS = [
    (re.compile(r"^\s*(?:set\s+)?target\s+is\s+(.+)$", re.I),      "set_target"),
    (re.compile(r"^\s*(?:set\s+)?target\s*[:= ]\s*(.+)$", re.I),   "set_target"),
    (re.compile(r"^\s*use\s+target\s+(.+)$", re.I),                "set_target"),
    (re.compile(r"^\s*(?:auto\s?run|auto\s?mode|autopilot|auto\s?chain|auto\s?attack)\b(.*)$", re.I),
                                                                   "start_auto"),
    (re.compile(r"^\s*(?:full\s+chain|run\s+full\s+chain|kill\s?chain)\b(.*)$", re.I),
                                                                   "start_auto"),
    (re.compile(r"^\s*(?:pause|stop|halt|wait)\s*$", re.I),        "pause"),
    (re.compile(r"^\s*(?:resume|continue|go)\s*$", re.I),          "resume"),
    (re.compile(r"^\s*(?:status|state|summary)\s*$", re.I),        "status"),
    (re.compile(r"^\s*(?:solve|run)\s+juice[- ]?shop\s*(.*)$", re.I), "juice_shop"),
    (re.compile(r"^\s*juice[- ]?shop\s+(list|status|all)\s*$", re.I), "juice_shop_cmd"),
    (re.compile(r"^\s*(?:teach|learn|explain|what\s+is|tell\s+me\s+about)\s+(.+)$", re.I),
                                                                   "teach"),
    (re.compile(r"^\s*(?:export\s+)?report\s*$", re.I),            "report"),
    (re.compile(r"^\s*generate\s+report\s*$", re.I),                "report"),
    (re.compile(r"^\s*(?:mode|switch)\s+(manual|auto)\s*$", re.I), "set_mode"),
]


def _match_tool(text):
    low = text.lower()
    hits = []
    for tool, aliases in TOOL_ALIASES.items():
        for a in aliases:
            if a in low:
                hits.append((len(a), tool))
    if hits:
        hits.sort(reverse=True)
        return hits[0][1]
    return None


def _extract_target(text):
    m = TARGET_PATTERN.search(text)
    if not m:
        return None
    return m.group(1).rstrip(".,;:!?")


def _build_nmap_args(text, target):
    flags = []
    low = text.lower()
    for phrase, flag in NMAP_SCAN_FLAGS.items():
        if phrase in low:
            for f in flag.split():
                if f not in flags:
                    flags.append(f)
    if not flags:
        flags = ["-sV", "--top-ports", "1000"]
    flags.append(target)
    return flags


def _probe_spa_length(url):
    """SPA detection: if GET /random-nonexistent returns a substantial 200
    body, gobuster needs --exclude-length. Returns body length or None."""
    try:
        import urllib.request, uuid
        probe = f"{url.rstrip('/')}/err0rs-probe-{uuid.uuid4().hex[:8]}"
        req = urllib.request.Request(probe, method="GET")
        req.add_header("User-Agent", "Mozilla/5.0 ERR0RS-probe")
        with urllib.request.urlopen(req, timeout=5) as r:
            body = r.read()
        if r.status == 200 and len(body) > 1000:
            return len(body)
    except Exception:
        pass
    return None


def _fast_parse(text, state=None):
    text = text.strip()
    low = text.lower()

    for pat, action in CONTROL_PATTERNS:
        m = pat.match(text)
        if not m: continue
        if action == "set_target":
            return {"action":"set_target","target":m.group(1).strip(),"confidence":0.99}
        if action == "set_mode":
            return {"action":"set_mode","mode":m.group(1).lower(),"confidence":0.99}
        if action == "start_auto":
            tail = m.group(1).strip() if m.lastindex else ""
            target = _extract_target(tail) or _extract_target(text)
            goal = "full_chain"
            if "cred" in low or "password" in low:        goal = "get_creds"
            elif "sqli" in low or "sql injection" in low: goal = "find_sqli"
            elif "xss" in low:                            goal = "find_xss"
            elif "rce" in low or "shell" in low:          goal = "get_shell"
            return {"action":"start_auto","target":target,"goal":goal,"confidence":0.95}
        if action in ("pause","resume","status","report"):
            return {"action":action,"confidence":0.99}
        if action == "juice_shop":
            # "solve juice-shop" → solve_all; "solve juice-shop <challenge-id>" → specific
            rest = m.group(1).strip() if m.lastindex else ""
            if not rest or rest.lower() in ("all","every","everything"):
                return {"action":"juice_shop","sub":"all","confidence":0.99}
            return {"action":"juice_shop","sub":"solve","challenge":rest,"confidence":0.97}
        if action == "juice_shop_cmd":
            sub = m.group(1).lower()
            return {"action":"juice_shop","sub":sub,"confidence":0.99}
        if action == "teach":
            return {"action":"teach","topic":m.group(1).strip(),"confidence":0.95}

    # Direct shell passthrough
    if text.startswith("$") or text.startswith("!"):
        raw = text[1:].strip()
        first = raw.split()[0] if raw else ""
        if first in TOOL_ALIASES:
            return {"action":"run_tool","tool":first,
                    "args":raw.split()[1:],"target":_extract_target(raw),
                    "confidence":0.99,"reason":"direct shell command"}


    tool = _match_tool(text)
    target = _extract_target(text)

    if tool:
        if tool == "nmap":
            effective_target = target or (state.target if state else None)
            if not effective_target:
                return {"action":"ask_user",
                        "question":"What's the target for nmap? IP, CIDR, or hostname?",
                        "question_key":"need_target","confidence":0.98}
            args = _build_nmap_args(text, effective_target)
            return {"action":"run_tool","tool":"nmap","args":args,
                    "target":effective_target,"confidence":0.95,
                    "reason":f"Port scan to map attack surface of {effective_target}"}

        # Check if text already contains flags (user gave full command)
        has_flags = any(tok.startswith("-") for tok in text.split())

        if not target and state and state.target:
            target = state.target
        if not target:
            return {"action":"ask_user",
                    "question":f"What's the target for {tool}?",
                    "question_key":"need_target","confidence":0.9}

        # Pass-through mode — user supplied flags, honor them verbatim
        if has_flags:
            # Strip the tool alias from the beginning of the text, keep the rest
            import shlex
            try:
                tokens = shlex.split(text)
            except ValueError:
                tokens = text.split()
            # Find the first occurrence of the canonical tool name or alias
            low_tokens = [t.lower() for t in tokens]
            start_idx = 0
            for alias in TOOL_ALIASES.get(tool, [tool]):
                if alias in low_tokens:
                    start_idx = low_tokens.index(alias) + 1
                    break
            # Everything after the tool name is its args
            args = tokens[start_idx:] if start_idx else tokens
            return {"action":"run_tool","tool":tool,"args":args,
                    "target":target,"confidence":0.92,
                    "reason":f"{tool} with operator-supplied flags"}

        # No flags — inject sensible defaults per tool
        args = []
        if tool == "nikto":
            args = ["-h", target if target.startswith("http") else f"http://{target}",
                    "-maxtime", "120"]
        elif tool == "sqlmap":
            url = target if target.startswith("http") else f"http://{target}"
            args = ["-u", url, "--batch", "--random-agent",
                    "--level=2", "--risk=1",
                    "--time-sec=3", "--timeout=15"]
        elif tool == "gobuster":
            url = target if target.startswith("http") else f"http://{target}"
            spa_len = _probe_spa_length(url)
            args = ["dir", "-u", url,
                    "-w", "/usr/share/wordlists/dirb/common.txt",
                    "-t", "30", "-q", "-b", "404,500"]
            if spa_len:
                args += ["--exclude-length", str(spa_len)]
        elif tool == "whatweb":
            url = target if target.startswith("http") else f"http://{target}"
            args = [url, "-a3"]
        elif tool == "dalfox":
            url = target if target.startswith("http") else f"http://{target}"
            if "#" in url:
                url = url.split("#")[0]
            args = ["url", url]
        elif tool == "nuclei":
            url = target if target.startswith("http") else f"http://{target}"
            args = ["-u", url, "-severity", "medium,high,critical",
                    "-silent", "-no-update-check"]
        elif tool == "wpscan":
            url = target if target.startswith("http") else f"http://{target}"
            args = ["--url", url, "--enumerate", "p,u"]

        return {"action":"run_tool","tool":tool,"args":args,
                "target":target,"confidence":0.85,
                "reason":f"{tool} requested for {target}"}

    return None


OLLAMA_SYSTEM_PROMPT = """You are ERR0RS, a penetration testing assistant.
Classify the operator's message into a JSON intent. Reply ONLY with valid JSON, no prose.

Schema:
{
  "action": "run_tool"|"set_target"|"start_auto"|"teach"|"ask_user"|"chat",
  "tool":   "nmap"|"nikto"|"sqlmap"|"gobuster"|"hydra"|"nuclei"|"whatweb"|"dalfox"|"metasploit"|"ffuf"|"wpscan"|"enum4linux"|"crackmapexec"|"aircrack"|"hashcat"|"subfinder"|null,
  "target": "<IP/CIDR/hostname/URL or null>",
  "args":   ["list","of","cli","flags"],
  "reason": "<1-sentence why>",
  "confidence": 0.0-1.0
}

Rules:
- If input isn't about pentesting → action="chat"
- If target missing → action="ask_user", question="<ask for target>"
- Stick to listed tools only
- For nmap syn scan use ["-sS","<target>"]
"""

def _ollama_parse(text, state=None):
    try:
        prompt = OLLAMA_SYSTEM_PROMPT + f"\n\nOperator message: {text}\n\nJSON intent:"
        proc = subprocess.run(
            ["ollama","run","qwen2.5-coder:7b",prompt],
            capture_output=True, text=True, timeout=20,
        )
        raw = proc.stdout.strip()
        m = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", raw, re.DOTALL)
        if not m: return None
        intent = json.loads(m.group(0))
        intent.setdefault("confidence", 0.6)
        intent.setdefault("action", "chat")
        return intent
    except Exception as e:
        log.warning(f"Ollama fallback failed: {e}")
        return None


def parse(text, state=None):
    """Main entry — fast path first, LLM fallback, else chat."""
    text = (text or "").strip()
    if not text:
        return {"action":"chat","confidence":0.0}
    fast = _fast_parse(text, state)
    if fast and fast.get("confidence", 0) >= 0.7:
        return fast
    slow = _ollama_parse(text, state)
    if slow:
        return slow
    return {"action":"chat","confidence":0.3}
