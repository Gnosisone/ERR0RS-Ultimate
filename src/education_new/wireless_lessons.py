#!/usr/bin/env python3
"""
ERR0RS Wireless / RF / Flipper Zero Lesson Pack
Source: tobiabocchi/flipperzero-bruteforce + lanjelot/wifi notes + ERR0RS RF knowledge

Covers: Sub-GHz OOK bruteforce, fixed-code protocols, RF recon, Flipper workflows
Plugs into teach_engine.py via ATTCK_KEYWORD_MAP + WIRELESS_LESSONS dict

Author: Gary Holden Schneider (Eros) | ERR0RS-Ultimate
"""

WIRELESS_LESSONS = {

  # ══════════════════════════════════════════════════════════════════════════
  # FLIPPER ZERO — Sub-GHz OOK Bruteforce
  # ══════════════════════════════════════════════════════════════════════════

  "subghz bruteforce": {
    "title": "Sub-GHz OOK Bruteforce (Flipper Zero)",
    "tldr": (
      "Brute force fixed-code Sub-GHz remotes (garage doors, gates, barriers) "
      "using Flipper Zero .sub files — works on CAME, NICE, Linear, Chamberlain, Holtek."
    ),
    "what": (
      "Many RF remotes (garage doors, gate openers, barrier arms, pagers) use "
      "'fixed code' OOK (On-Off Keying) modulation — they always transmit the SAME "
      "code every button press, with NO rolling code protection.\n\n"
      "This means if you enumerate all possible codes for the protocol, one of them "
      "WILL open the target. The attack is purely physical-layer — no crypto to break.\n\n"
      "Fixed-code protocols targeted:\n"
      "  CAME     — 12-bit, 433/868 MHz, ~224 seconds to brute force\n"
      "  NICE     — 12-bit, 433/868 MHz, ~628 seconds\n"
      "  Linear   — 10-bit, 300/310 MHz, ~212 seconds\n"
      "  Chamberlain — 9-bit, 300/315/390 MHz, ~123 seconds\n"
      "  Holtek   — 12-bit, 315/433/868/915 MHz, ~387 seconds\n"
      "  Ansonic  — 12-bit, 434 MHz, ~276 seconds\n\n"
      "NOTE: Modern rolling-code systems (KeeLoq, AUT64) are NOT vulnerable to this. "
      "This only works on legacy fixed-code hardware."
    ),
    "how": (
      "The attack uses a binary search tree approach to efficiently find the key:\n\n"
      "  1. Play the SINGLE full bruteforce file — confirms attack works on target\n"
      "  2. Play the TWO half-files (2048 keys each) — find which half has the key\n"
      "  3. Play the two quarter-files of the winning half — narrow further\n"
      "  4. Keep halving until you reach files of ~128 keys (~10 seconds each)\n\n"
      "Timing formula per protocol:\n"
      "  (pilot_period + n_bits × bit_period) × repetitions × 2^n_bits\n\n"
      "CAME example: (9000 + 12×750) × 3 × 4096 ≈ 224 seconds total\n\n"
      "Binary search: 12-bit protocol = 4096 codes. After first split you check\n"
      "2048, then 1024, then 512... down to ~10 seconds per file = ~7 splits."
    ),
    "phases": [
      "1. RECON — identify target frequency with Flipper Sub-GHz → Frequency Analyzer",
      "2. CAPTURE — record a genuine transmission to identify the protocol",
      "3. IDENTIFY — match waveform timing to known protocol (CAME/NICE/Linear etc.)",
      "4. GENERATE — run flipperzero-bruteforce.py to create .sub files for that protocol",
      "5. TRANSFER — copy .sub files to Flipper SD card (SD/subghz/bruteforce/)",
      "6. EXECUTE — play full file to confirm, then binary search to find exact key",
      "7. REPLAY — replay the exact key file (128 keys, ~10 sec) to operate target",
    ],
    "commands": {
      "Generate all .sub files":     "python3 flipperzero-bruteforce.py",
      "Generate specific protocol":  "# Edit protocols list in script, comment out others",
      "CAME 12-bit 433MHz timing":   "224 seconds full bruteforce (3.7 min)",
      "NICE 12-bit 433MHz timing":   "628 seconds full bruteforce (10.5 min)",
      "Linear 10-bit 300MHz timing": "212 seconds full bruteforce (3.5 min)",
      "Chamberlain 9-bit timing":    "123 seconds full bruteforce (2 min)",
      "Flipper Sub-GHz read":        "Flipper → Sub-GHz → Read → point at remote",
      "Flipper frequency scan":      "Flipper → Sub-GHz → Frequency Analyzer",
      "Flipper replay":              "Flipper → Sub-GHz → Saved → select .sub file → Send",
      "Copy to Flipper SD":          "cp sub_files/CAME-12bit-433/* /media/kali/FlipperSD/subghz/bruteforce/",
      "Add custom protocol": (
        'Protocol("MYPROTO", 12,\n'
        '  {"0": "-320 640 ", "1": "-640 320 "},\n'
        '  "-11520 320 ")  # pilot period'
      ),
    },
    "flags": {
      "Frequency Analyzer":  "Flipper built-in — shows strongest signal frequency in real time",
      "RogueMaster":         "Your firmware — has extended Sub-GHz freq range + extra protocols",
      "OOK":                 "On-Off Keying — RF modulation used by most fixed-code remotes",
      "pilot_period":        "Preamble transmitted before each key — protocol-specific pattern",
      "stop_bit":            "Trailing pattern after each key — some protocols require it",
      "repetition":          "Number of times each code is transmitted (usually 3x for reliability)",
      "debruijn.sub":        "De Bruijn sequence file — theoretical optimal but unreliable in practice",
    },
    "defense": (
      "✅ Use rolling code systems (KeeLoq, AUT64, HCS301) — each press generates unique code\n"
      "✅ Upgrade legacy fixed-code remotes — many are 20+ year old tech\n"
      "✅ Add secondary authentication (PIN pad, app-based, encrypted challenge-response)\n"
      "✅ RF signal monitoring — alert on extended transmission bursts near access points\n"
      "✅ Wired backup control — don't rely solely on RF for critical access\n"
      "✅ Site survey: identify all RF-controlled access points and audit their protocol age"
    ),
    "tips": [
      "CAME 12-bit is the most common garage/gate protocol in Europe — start here",
      "Linear/Chamberlain dominate North America — check frequency (Linear=300/310, Chamber=315/390)",
      "Frequency Analyzer on Flipper shows you exactly what freq the remote uses",
      "Binary search: 12 bits = worst case 12 transmissions to find exact key",
      "The pre-built .sub files in the repo cover most common protocols — no need to generate",
      "RogueMaster firmware extends Sub-GHz TX range — gives you more distance on attack",
      "Use the CAME-fast variant when available — same result, 21% faster (224s vs 287s)",
      "Record target remote first with Flipper — confirms you have the right protocol before bruteforcing",
    ],
    "mitre": "T1190 — Physical access via RF / T0803 — Block Reporting Message (ICS)",
  },

  # ── Aliases ──────────────────────────────────────────────────────────────
  "flipper bruteforce":      "subghz bruteforce",
  "ook bruteforce":          "subghz bruteforce",
  "subghz":                  "subghz bruteforce",
  "sub-ghz bruteforce":      "subghz bruteforce",
  "rf bruteforce":           "subghz bruteforce",
  "garage door bruteforce":  "subghz bruteforce",
  "came":                    "subghz bruteforce",
  "fixed code":              "subghz bruteforce",
  "flipper rf":              "subghz bruteforce",

}


_WIRELESS_ALIASES = {
    "flipper bruteforce":     "subghz bruteforce",
    "ook bruteforce":         "subghz bruteforce",
    "subghz":                 "subghz bruteforce",
    "sub-ghz bruteforce":     "subghz bruteforce",
    "rf bruteforce":          "subghz bruteforce",
    "garage door bruteforce": "subghz bruteforce",
    "came":                   "subghz bruteforce",
    "fixed code":             "subghz bruteforce",
    "flipper rf":             "subghz bruteforce",
}


def resolve_wireless_lesson(keyword: str):
    """Resolve aliases and return correct WIRELESS_LESSONS entry."""
    kw = keyword.lower().strip()
    kw = _WIRELESS_ALIASES.get(kw, kw)
    lesson = WIRELESS_LESSONS.get(kw)
    if isinstance(lesson, str):
        lesson = WIRELESS_LESSONS.get(lesson)
    if lesson and isinstance(lesson, dict) and lesson.get("what"):
        return lesson
    # substring fallback
    for key, val in WIRELESS_LESSONS.items():
        if key and isinstance(val, dict) and val.get("what") and key in kw:
            return val
    return None
