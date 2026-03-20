#!/usr/bin/env python3
"""
ERR0RS — RocketGod Knowledge Module
Indexes all RocketGod repos: Flipper SD, RF Jammer, ProtoPirate,
SubGHz Toolkit, HackRF Treasure Chest, Radio Scanner, SUB Analyzer,
Signal Generator, WiGLE Vault, DFU Extractor, Ghidra Porter, Carjacker
Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

from pathlib import Path
from typing import Optional, List, Dict

ROOT_DIR = Path(__file__).resolve().parents[2]
RG_DIR   = ROOT_DIR / "knowledge" / "rocketgod"

ROCKETGOD_REPOS = {
    "Flipper_Zero": {
        "path": RG_DIR / "Flipper_Zero", "stars": 1440,
        "description": "RocketGod's complete Flipper Zero SD drive — the ultimate community resource",
        "categories": {
            "badusb":"BadUSB scripts — Windows + macOS",
            "subghz":"Sub-GHz captures: garages, doorbells, remotes, Tesla",
            "infrared":"IR: TVs, ACs, fans, projectors, consoles, cameras",
            "nfc":"NFC: Amiibo, YouTube tricks, HID iClass",
            "music_player":"100+ RTTTL songs",
            "wav_player":"WAV audio files",
            "lfrfid":"Low-frequency RFID dumps",
            "flipper_toolbox":"Python scripts: subghz gen, NFC gen, IR gen",
            "wetox_scripts":"SubGHz analysis and NFC tools",
            "unirf":"UniRF map files",
            "subplaylist":"SubGHz playlist files for automated replay",
            "Dolphin_Level":"XP level state files — unlock all Flipper levels",
            "Wifi_DevBoard":"WiFi dev board schematic + Marauder flasher",
            "shopping-carts":"Shopping cart wheel signal captures",
        },
        "tags":["flipper","sd","badusb","subghz","nfc","ir","rfid","music","complete"],
    },
    "flipper-zero-rf-jammer": {
        "path": RG_DIR / "flipper-zero-rf-jammer", "stars": 632,
        "description": "SubGHz RF jammer with 13+ modes across 300-928MHz",
        "modes": {
            "OOK 650kHz":      "Overwhelms garage doors, key fobs (continuous 0xFF)",
            "2FSK 2.38kHz":    "Narrow FSK — disrupts low-data-rate remotes",
            "2FSK 47.6kHz":    "Wide FSK — broader spectrum disruption",
            "MSK 99.97Kb/s":   "Random data — jams high-speed digital links",
            "GFSK 9.99Kb/s":   "Disrupts Bluetooth, Zigbee, low-power IoT",
            "Bruteforce 0xFF": "Most aggressive — constant carrier, jams everything",
            "Sine Wave":       "Analog modulation interference",
            "Square Wave":     "Digital pulse jamming",
            "Sawtooth Wave":   "Frequency sweep interference",
            "White Noise":     "Universal broadband noise",
            "Triangle Wave":   "Symmetric frequency oscillation",
            "Chirp Signal":    "Rising frequency — overloads radar/sonar receivers",
            "Gaussian Noise":  "Mimics natural RF interference — hard to detect",
            "Burst Mode":      "Packetized bursts — confuses burst comm systems",
        },
        "bands":["300-348 MHz","387-464 MHz","779-928 MHz"],
        "tags":["rf","jammer","subghz","flipper","cc1101","ook","fsk"],
    },
    "ProtoPirate": {
        "path": RG_DIR / "ProtoPirate", "stars": 445,
        "description": "Rolling-code analysis toolkit — decode/encode automotive key fobs",
        "protocols": ["Fiat","Ford","Kia V0-V6","Scher-Khan","StarLine",
                      "Subaru","Suzuki","PSA","VAG/VW/Audi"],
        "features": [
            "Real-time signal capture with animated radar",
            "Load/analyze .sub files from SD",
            "Timing Tuner for protocol dev",
            "Frequency hopping support",
            "No TX by default (safe for testing)",
        ],
        "tags":["rolling code","keyfob","automotive","subghz","kia","ford","vw"],
    },
    "SubGHz-Toolkit": {
        "path": RG_DIR / "SubGHz-Toolkit", "stars": 223,
        "description": "Reverse engineer SubGHz protocols + Keeloq manufacturer codes",
        "tags":["subghz","keeloq","reverse engineering","protocol","flipper"],
    },
    "HackRF-Treasure-Chest": {
        "path": RG_DIR / "HackRF-Treasure-Chest", "stars": 680,
        "description": "HackRF software, captures, tools — everything SDR/HackRF",
        "tags":["hackrf","sdr","captures","rf","spectrum","gnuradio"],
    },
    "Flipper-Zero-Radio-Scanner": {
        "path": RG_DIR / "Flipper-Zero-Radio-Scanner", "stars": 105,
        "description": "Radio frequency scanner for Flipper Zero — outputs to internal speaker",
        "tags":["flipper","radio","scanner","subghz","cc1101"],
    },
    "Flipper-Zero-SUB-Analyzer": {
        "path": RG_DIR / "Flipper-Zero-SUB-Analyzer", "stars": 48,
        "description": "Extract all signal data from a Flipper Zero .sub file",
        "tags":["flipper","subghz","sub","analyzer","signal","protocol"],
    },
    "SubGHz-Signal-Generator": {
        "path": RG_DIR / "SubGHz-Signal-Generator", "stars": 34,
        "description": "SubGHz signal generator for Flipper Zero",
        "tags":["flipper","subghz","signal","generator"],
    },
    "flipper-zero-carjacker": {
        "path": RG_DIR / "flipper-zero-carjacker", "stars": 157,
        "description": "Flipper Zero Carjacker App — rolling code analysis (educational)",
        "tags":["flipper","car","keyfob","subghz","automotive","rolling code"],
    },
    "ghidra-firmware-symbol-porter": {
        "path": RG_DIR / "ghidra-firmware-symbol-porter", "stars": 13,
        "description": "Port symbols between firmware binaries using Ghidra for reverse engineering",
        "tags":["ghidra","reverse engineering","firmware","symbols","flipper"],
    },
    "DFU-Binary-Extractor": {
        "path": RG_DIR / "DFU-Binary-Extractor", "stars": 34,
        "description": "Extract raw firmware from DFU containers for reverse engineering",
        "tags":["dfu","firmware","extraction","reverse engineering","flipper"],
    },
    "WiGLE-Vault": {
        "path": RG_DIR / "WiGLE-Vault", "stars": 2,
        "description": "Download all WiGLE wardriving data — backup WiFi survey history",
        "tags":["wigle","wardriving","wifi","osint","geolocation"],
    },
    "Dark-Web-Discord-Bot": {
        "path": RG_DIR / "Dark-Web-Discord-Bot", "stars": 0,
        "description": "Discord bot searching dark web via ahmia.fi — returns links + screenshots",
        "tags":["discord","darkweb","osint","ahmia","bot","python"],
    },
}

FLIPPER_TOOLBOX_SCRIPTS = {
    "subghz_gen_cmd.py":     "Generate SubGHz command .sub files from parameters",
    "subghz_ook_to_sub.py":  "Convert OOK signal data to Flipper .sub format",
    "subghz_preset_gen.py":  "Generate custom SubGHz radio preset files",
    "subghz_histogram.py":   "Analyze and plot signal timing histograms",
    "subghz_create_dat.py":  "Create SubGHz raw data files",
    "subghz_insteon.py":     "Insteon home automation SubGHz protocol support",
    "subghz_x10.py":         "X10 home automation SubGHz protocol support",
    "nfc_gen_url.py":         "Generate NFC URL tag .nfc files",
    "nfc_gen_wifi.py":        "Generate NFC WiFi config tag files",
    "nfc_gen_phone.py":       "Generate NFC phone contact tag files",
    "nfc_hexdump.py":         "Hexdump and analyze NFC file contents",
    "nfc_prox2flip.py":       "Convert Proxmark data to Flipper NFC format",
    "ir_gen_all_codes.py":    "Generate all IR codes for a target device",
    "ir_plot.py":             "Plot and visualize IR signal timing",
}


class RocketGodKB:
    """Knowledge base for all RocketGod repos"""

    def __init__(self):
        self.indexed = {}
        self._index()

    def _index(self):
        """Walk all repos and catalog files"""
        for repo_name, meta in ROCKETGOD_REPOS.items():
            path = meta["path"]
            if not path.exists():
                continue
            files = []
            for ext in [".txt",".sub",".ir",".nfc",".py",".ps1",".md",".rfid",".fmf"]:
                files.extend(path.rglob(f"*{ext}"))
            self.indexed[repo_name] = {
                "meta":  meta,
                "files": [str(f) for f in files[:500]],  # cap at 500
                "count": len(files),
            }

    def search(self, query: str, limit: int = 8) -> list:
        """Search across all RocketGod repos"""
        q = query.lower()
        results = []
        for repo_name, data in self.indexed.items():
            meta  = data["meta"]
            score = 0
            blob  = " ".join([
                meta.get("description",""),
                " ".join(meta.get("tags",[])),
                str(meta.get("categories",{})),
                str(meta.get("modes",{})),
                str(meta.get("protocols",[])),
                str(meta.get("features",[])),
            ]).lower()
            for word in q.split():
                if word in blob:
                    score += 2
            # Bonus: check if any filenames match
            for f in data.get("files",[]):
                if q in f.lower():
                    score += 1
                    break
            if score > 0:
                results.append((score, repo_name, meta))
        results.sort(key=lambda x: x[0], reverse=True)
        return [{"repo": r[1], "meta": r[2], "score": r[0]} for r in results[:limit]]

    def get_sub_files(self, category: str = None) -> list:
        """Get .sub files from Flipper_Zero SD drive"""
        fz = self.indexed.get("Flipper_Zero", {})
        subs = [f for f in fz.get("files",[]) if f.endswith(".sub")]
        if category:
            subs = [f for f in subs if category.lower() in f.lower()]
        return subs

    def get_ir_files(self, device_type: str = None) -> list:
        """Get .ir files from Flipper_Zero SD drive"""
        fz = self.indexed.get("Flipper_Zero", {})
        irs = [f for f in fz.get("files",[]) if f.endswith(".ir")]
        if device_type:
            irs = [f for f in irs if device_type.lower() in f.lower()]
        return irs

    def get_toolbox_scripts(self) -> dict:
        """Get flipper_toolbox Python scripts"""
        return FLIPPER_TOOLBOX_SCRIPTS

    def get_jammer_modes(self) -> dict:
        """Get RF jammer mode descriptions"""
        jammer = ROCKETGOD_REPOS.get("flipper-zero-rf-jammer",{})
        return jammer.get("modes",{})

    def get_protopirate_protocols(self) -> list:
        """Get ProtoPirate supported protocols"""
        pp = ROCKETGOD_REPOS.get("ProtoPirate",{})
        return pp.get("protocols",[])

    def summary(self) -> dict:
        """Return summary of all indexed repos"""
        out = {}
        for repo, data in self.indexed.items():
            out[repo] = {
                "stars":       data["meta"].get("stars", 0),
                "description": data["meta"].get("description",""),
                "files":       data["count"],
                "tags":        data["meta"].get("tags",[]),
            }
        return out


def handle_rocketgod_request(request, params: dict = None) -> dict:
    """
    API handler for /api/rocketgod endpoint.

    Supports TWO call styles for full launcher compatibility:

      Style A — dict payload (used by errorz_launcher.py + /api/rocketgod):
        handle_rocketgod_request({"action": "jammer_modes"})
        handle_rocketgod_request({"action": "search", "prompt": "flipper badusb"})

      Style B — command string (legacy/external callers per integration spec):
        handle_rocketgod_request("jammer_modes")
        handle_rocketgod_request("search", {"prompt": "flipper badusb"})

    Actions: search | summary | sub_files | ir_files | jammer_modes |
             protopirate | toolbox | hackrf | execute | status
    """
    # ── Dual-signature normalization ──────────────────────────────────────
    if isinstance(request, str):
        # Style B: (command: str, params: dict) → normalize to dict
        action = request
        extra  = params or {}
        request = {"action": action, **extra}
    # Style A: (request: dict) — already correct, fall through
    kb     = RocketGodKB()
    action = request.get("action", "summary")

    if action == "search":
        results = kb.search(request.get("prompt",""), limit=request.get("limit",8))
        return {"status":"ok","results":[
            {"repo":r["repo"],"description":r["meta"].get("description",""),
             "tags":r["meta"].get("tags",[]),"score":r["score"]}
            for r in results
        ]}

    elif action == "summary":
        return {"status":"ok","repos":kb.summary()}

    elif action == "sub_files":
        files = kb.get_sub_files(request.get("category"))
        return {"status":"ok","count":len(files),"files":files[:50]}

    elif action == "ir_files":
        files = kb.get_ir_files(request.get("device_type"))
        return {"status":"ok","count":len(files),"files":files[:50]}

    elif action == "jammer_modes":
        return {"status":"ok","modes":kb.get_jammer_modes()}

    elif action == "protopirate":
        return {"status":"ok",
                "protocols":kb.get_protopirate_protocols(),
                "features":ROCKETGOD_REPOS["ProtoPirate"]["features"]}

    elif action == "toolbox":
        return {"status":"ok","scripts":kb.get_toolbox_scripts()}

    elif action == "hackrf":
        repo = ROCKETGOD_REPOS["HackRF-Treasure-Chest"]
        return {"status":"ok",
                "description":repo["description"],
                "path":str(repo["path"]),
                "tags":repo["tags"]}

    elif action == "execute":
        # Style B compat: run a named RocketGod command
        # Internally maps to the closest existing action
        command = request.get("command", request.get("prompt", ""))
        print(f"[RocketGod] Processing: {command}")
        # Route to search — most useful interpretation of a freeform command
        results = kb.search(command, limit=5) if command else []
        return {
            "status":  "success",
            "output":  f"Executed {command}",
            "results": [
                {"repo": r["repo"], "description": r["meta"].get("description", "")}
                for r in results
            ],
        }

    elif action == "status":
        indexed_count = len(kb.indexed)
        total_files   = sum(d["count"] for d in kb.indexed.values())
        return {
            "status":        "ok",
            "indexed_repos": indexed_count,
            "total_files":   total_files,
            "repos":         list(ROCKETGOD_REPOS.keys()),
            "note":          "Submodules must be cloned for full file indexing" if indexed_count == 0 else "Knowledge base active",
        }

    else:
        return {"status":"error","error":f"Unknown action: {action}"}


if __name__ == "__main__":
    import json
    kb = RocketGodKB()
    print("=== RocketGod Knowledge Base ===")
    for repo, info in kb.summary().items():
        print(f"  [{info['stars']:>5}★] {repo}: {info['files']} files — {info['description'][:60]}")
    print(f"\nTotal repos indexed: {len(kb.indexed)}")
    print(f"SUB files available: {len(kb.get_sub_files())}")
    print(f"IR files available:  {len(kb.get_ir_files())}")
