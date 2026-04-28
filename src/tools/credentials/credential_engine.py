#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Credential Engine v1.0
Centralized credential management, automated spraying, and analytics

Competes with: Pentera (credential-based automation),
               CrackMapExec (spray automation),
               Metasploit Pro (credential tracking)

Features:
  - Centralized credential store per engagement
  - Auto hash-type detection (NTLM, MD5, SHA1, bcrypt, NTLMv2, Kerberos TGS...)
  - Hash cracking pipeline (hashcat with auto mode detection)
  - Password spray automation with lockout protection
  - Credential reuse testing across SMB/SSH/RDP/WinRM
  - Password pattern analytics for reporting

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import subprocess, json, shutil, re, hashlib
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field

CRED_DIR = Path(__file__).parents[3] / "output" / "credentials"
CRED_DIR.mkdir(parents=True, exist_ok=True)

HASH_PATTERNS = [
    (r"^[0-9a-f]{32}$",                                  "0",     "MD5"),
    (r"^[0-9a-f]{40}$",                                  "100",   "SHA1"),
    (r"^[0-9a-f]{64}$",                                  "1400",  "SHA256"),
    (r"^[0-9a-f]{32}:[0-9a-f]{32}$",                     "1000",  "NTLM"),
    (r"^\$2[aby]\$",                                      "3200",  "bcrypt"),
    (r"^\$6\$",                                           "1800",  "sha512crypt"),
    (r"^\$1\$",                                           "500",   "md5crypt"),
    (r"^[^:]+::[^:]+:[0-9a-f]+:[0-9a-f]+:[0-9a-f]+$",   "5600",  "NetNTLMv2"),
    (r"^\$krb5tgs\$",                                     "13100", "Kerberos TGS"),
    (r"^\$krb5asrep\$",                                   "18200", "AS-REP Roast"),
    (r"^\$DCC2\$",                                        "2100",  "DCC2"),
]


def detect_hash_type(h: str) -> tuple:
    for pattern, mode, name in HASH_PATTERNS:
        if re.match(pattern, h.strip(), re.IGNORECASE):
            return (mode, name)
    return ("", "unknown")


@dataclass
class CredEntry:
    id:          str  = field(default_factory=lambda: hashlib.md5(
                              datetime.now().isoformat().encode()).hexdigest()[:8])
    username:    str  = ""
    domain:      str  = ""
    secret:      str  = ""
    secret_type: str  = "unknown"
    hash_mode:   str  = ""
    cracked:     bool = False
    plaintext:   str  = ""
    source:      str  = ""
    target:      str  = ""
    service:     str  = ""
    timestamp:   str  = field(default_factory=lambda: datetime.now().isoformat())


class CredentialEngine:
    def __init__(self, engagement_id: str = "default"):
        self.engagement_id = engagement_id
        self.creds: list   = []
        self.store_path    = CRED_DIR / f"{engagement_id}_creds.json"
        self._load()

    def add(self, username: str, secret: str, domain: str = "",
            source: str = "", target: str = "", service: str = "") -> CredEntry:
        mode, name = detect_hash_type(secret)
        e = CredEntry(username=username, secret=secret, domain=domain,
                      secret_type=name, hash_mode=mode,
                      source=source, target=target, service=service)
        self.creds.append(e)
        self._save()
        return e

    def add_bulk(self, lines: list, source: str = "", target: str = "") -> int:
        added = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                if line.count(":") >= 4:  # secretsdump format
                    parts = line.split(":")
                    nt = parts[3] if len(parts) > 3 else ""
                    if nt and len(nt) == 32:
                        self.add(parts[0], nt, source=source, target=target, service="windows")
                        added += 1; continue
                if ":" in line:
                    left, right = line.split(":", 1)
                    domain, user = ("", left)
                    if "/" in left or "\\" in left:
                        sep = "/" if "/" in left else "\\"
                        domain, user = left.split(sep, 1)
                    self.add(user, right, domain=domain, source=source, target=target)
                    added += 1
            except Exception:
                pass
        return added

    def get_uncracked(self) -> list:
        return [c for c in self.creds if not c.cracked and c.hash_mode]

    def get_cracked(self) -> list:
        return [c for c in self.creds if c.cracked and c.plaintext]

    def mark_cracked(self, cred_id: str, plaintext: str):
        for c in self.creds:
            if c.id == cred_id:
                c.cracked = True; c.plaintext = plaintext
                self._save(); return

    def crack_all(self, wordlist: str = "/usr/share/wordlists/rockyou.txt",
                  rules: str = "") -> dict:
        if not shutil.which("hashcat"):
            return {"status": "error", "message": "hashcat not installed"}
        uncracked = self.get_uncracked()
        if not uncracked:
            return {"status": "ok", "message": "No hashes to crack"}
        by_mode: dict = {}
        for c in uncracked:
            if c.hash_mode:
                by_mode.setdefault(c.hash_mode, []).append(c)
        results = {"cracked": 0, "modes": []}
        for mode, entries in by_mode.items():
            hf  = CRED_DIR / f"hashes_{mode}.txt"
            of  = CRED_DIR / f"cracked_{mode}.txt"
            hf.write_text("\n".join(e.secret for e in entries))
            rf  = f"-r {rules}" if rules else ""
            cmd = (f"hashcat -m {mode} -a 0 {hf} {wordlist} {rf} "
                   f"--outfile {of} --outfile-format=2 --force -q 2>/dev/null")
            try:
                subprocess.run(cmd, shell=True, timeout=600)
                pairs = self._parse_cracked(of)
                for secret, plain in pairs.items():
                    for e in entries:
                        if e.secret.lower() == secret.lower():
                            self.mark_cracked(e.id, plain)
                            results["cracked"] += 1
                results["modes"].append({"mode": mode, "attempted": len(entries)})
            except subprocess.TimeoutExpired:
                pass
        self._save()
        return results

    def _parse_cracked(self, path: Path) -> dict:
        pairs = {}
        if path.exists():
            for line in path.read_text().splitlines():
                if ":" in line:
                    h, p = line.rsplit(":", 1)
                    pairs[h] = p
        return pairs

    def spray(self, targets: list, service: str = "smb",
              max_rounds: int = 3, delay_s: int = 30) -> dict:
        if not shutil.which("crackmapexec"):
            return {"status": "error", "message": "crackmapexec not installed"}
        cracked = self.get_cracked()
        if not cracked:
            return {"status": "error", "message": "No cracked passwords to spray"}
        users   = list(set(c.username for c in cracked))
        pwds    = list(set(c.plaintext for c in cracked if c.plaintext))[:max_rounds]
        target_str = " ".join(targets)
        hits    = []
        for i, pwd in enumerate(pwds):
            for user in users:
                cmd = (f"crackmapexec {service} {target_str} "
                       f"-u '{user}' -p '{pwd}' --continue-on-success 2>/dev/null")
                try:
                    r = subprocess.run(cmd, shell=True, capture_output=True,
                                       text=True, timeout=60)
                    for line in (r.stdout + r.stderr).splitlines():
                        if "[+]" in line:
                            hits.append({"user": user, "password": pwd,
                                         "service": service, "line": line.strip()})
                except subprocess.TimeoutExpired:
                    pass
            if i < len(pwds) - 1:
                import time; time.sleep(delay_s)
        return {"hits": hits, "total": len(hits)}

    def analyze_patterns(self) -> str:
        cracked = self.get_cracked()
        if not cracked:
            return "No cracked passwords to analyze."
        passwords = [c.plaintext for c in cracked]
        checks = {
            "Season+Year":    lambda p: bool(re.search(r"(spring|summer|fall|winter)\d{2,4}", p, re.I)),
            "Company+Number": lambda p: bool(re.search(r"[A-Za-z]{3,}\d{2,4}[!@#]?$", p)),
            "Length < 8":     lambda p: len(p) < 8,
            "No special char":lambda p: not re.search(r"[!@#$%^&*]", p),
            "All lowercase":  lambda p: p.islower(),
        }
        lines = [f"PASSWORD PATTERNS ({len(passwords)} cracked):", ""]
        for label, fn in checks.items():
            count = sum(1 for p in passwords if fn(p))
            lines.append(f"  {label:<22} {count}/{len(passwords)} ({count/len(passwords)*100:.0f}%)")
        return "\n".join(lines)

    def summary(self) -> str:
        total   = len(self.creds)
        cracked = len(self.get_cracked())
        by_type: dict = {}
        for c in self.creds:
            by_type[c.secret_type] = by_type.get(c.secret_type, 0) + 1
        lines = [f"\n[CRED ENGINE] Engagement: {self.engagement_id}", "="*42,
                 f"  Total: {total}  |  Cracked: {cracked}  |  "
                 f"Uncracked: {total - cracked}", "  Hash types:"]
        for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
            lines.append(f"    {t:<26} {n}")
        return "\n".join(lines)

    def _save(self):
        from dataclasses import asdict
        self.store_path.write_text(
            json.dumps([asdict(c) for c in self.creds], indent=2))

    def _load(self):
        if self.store_path.exists():
            try:
                self.creds = [CredEntry(**d)
                              for d in json.loads(self.store_path.read_text())]
            except Exception:
                self.creds = []


cred_engine = CredentialEngine()
