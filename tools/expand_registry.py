#!/usr/bin/env python3
"""
ERR0RS — Registry Expansion (Phase 2.5)
═══════════════════════════════════════
Takes the v2 hand-curated registry (49 tools) + the Phoenix-OS BlackArch
catalog (4,978 tools) + the popularity ranking, and produces v3.json:

  - All 4,978 BlackArch tools as registry entries
  - Hand-curated v2 entries preserved with full depth (flags, output_read,
    references) — the LLM generation never overwrites these
  - Each tool tagged with tier (1/2/3/4) based on popularity score:
      tier 1: score >= 30 (curated canon)
      tier 2: score >= 10 (popular + matches sec keywords)
      tier 3: score 5     (well-formed but esoteric)
      tier 4: score 0     (long tail)
  - Stub fields (opsec_notes, sample_outputs, legal_notes, false_positives,
    mitre_attack) empty initially — filled by generate_teach.py in batches

Usage:
  python3 tools/expand_registry.py            # dry-run, prints plan
  python3 tools/expand_registry.py --write    # actually write v3 file
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V2 = ROOT / 'src' / 'tools' / 'tool_registry.v2.json'
RANKED = ROOT / 'tools' / 'arsenal_ranked.json'
OUT = ROOT / 'src' / 'tools' / 'tool_registry.v3.json'
BLACKARCH = Path('/home/kali/Phoenix-OS/blackarch_metadata.json')


def normalize_key(name: str) -> str:
    """Convert tool name to canonical key (lowercase, hyphens/underscores)."""
    return re.sub(r'[^a-z0-9_-]', '', name.lower())


def score_to_tier(score: int) -> int:
    if score >= 30:
        return 1
    if score >= 10:
        return 2
    if score >= 5:
        return 3
    return 4


def categorize_from_desc(desc: str, name: str) -> str:
    """Best-effort category from BlackArch description."""
    desc = (desc or '').lower()
    name = name.lower()
    keywords = {
        'recon': ['recon', 'enum', 'subdomain', 'dns', 'osint', 'scan', 'port', 'discover'],
        'web': ['web', 'http', 'sql injection', 'xss', 'sqli', 'wordpress', 'cms', 'directory'],
        'exploitation': ['exploit', 'metasploit', 'shellcode', 'payload', 'cve'],
        'post-exploit': ['post-exploit', 'persistence', 'lateral', 'pivot'],
        'credentials': ['password', 'hash', 'crack', 'brute force', 'credential', 'kerberos'],
        'wireless': ['wifi', 'wireless', 'bluetooth', '802.11', 'wpa', 'aircrack'],
        'forensics': ['forensic', 'memory', 'disk', 'volatility', 'carving'],
        'reverse': ['reverse', 'disassem', 'debugger', 'binary', 'decompil', 'ghidra'],
        'evasion': ['evasion', 'av bypass', 'obfusc', 'amsi', 'etw', 'packer'],
        'social-engineering': ['phish', 'social', 'pretext', 'sms'],
        'mobile': ['android', 'ios', 'apk', 'mobile', 'frida'],
        'cloud': ['aws', 'azure', 'gcp', 'cloud', 's3', 'kubernetes', 'docker'],
        'container': ['docker', 'kubernetes', 'k8s', 'container', 'helm'],
        'ad': ['active directory', 'ldap', 'kerber', 'domain'],
        'network': ['network', 'sniff', 'mitm', 'pcap', 'arp'],
        'c2': ['c2', 'command and control', 'beacon', 'implant'],
        'hardware': ['rfid', 'sdr', 'firmware', 'flipper', 'badusb', 'hardware'],
    }
    for cat, kws in keywords.items():
        if any(kw in desc or kw in name for kw in kws):
            return cat
    return 'utility'


def build_v3(write: bool = False):
    v2 = json.load(open(V2))
    v2_tools = v2['tools']
    ranked = json.load(open(RANKED))
    blackarch = json.load(open(BLACKARCH))

    print(f"  v2 hand-curated tools:     {len(v2_tools)}")
    print(f"  BlackArch catalog:         {len(blackarch)}")
    print(f"  Ranked list:               {len(ranked)}")

    v3 = {}

    # 1. Start with EVERY hand-curated v2 entry, untouched
    for key, tool in v2_tools.items():
        v3[key] = dict(tool)
        # Ensure tier is set (v2 didn't have one consistently)
        v3[key].setdefault('tier', 1)

    # 2. For every BlackArch tool not already in v2, create a stub entry
    added = 0
    for entry in ranked:
        name = entry['name']
        key = normalize_key(name)
        if not key or key in v3:
            continue
        score = entry['score']
        tier = score_to_tier(score)
        meta = blackarch.get(name, {})
        desc = meta.get('desc') or ''
        v3[key] = {
            'display_name': name,
            'aliases': sorted({key, name.lower()}) if key != name.lower() else [key],
            'binary': name,
            'category': categorize_from_desc(desc, name),
            'phases': [],
            'tier': tier,
            'risk': 'moderate',
            'authorization_required': True,
            'description': desc[:160],
            'teach_intro': desc[:500],
            'default_flags': [],
            'default_command': '',
            'flags': {},
            'output_read': [],
            'opsec_notes': [],
            'sample_outputs': [],
            'legal_notes': [],
            'false_positives': [],
            'mitre_attack': [],
            'learning_path': {'prerequisites': [], 'leads_to': []},
            'common_pitfalls': [],
            'related_tools': [],
            'next_steps': [],
            'references': [
                {'type': 'official', 'url': meta['url']}
            ] if meta.get('url') else [],
        }
        added += 1

    print(f"\n  v3 total tools:            {len(v3)}")
    print(f"  Added from BlackArch:      {added}")

    # Tier breakdown
    tier_counts = {}
    for t in v3.values():
        tier_counts[t.get('tier', 4)] = tier_counts.get(t.get('tier', 4), 0) + 1
    print(f"\n  Tier breakdown:")
    print(f"    Tier 1 (curated canon):       {tier_counts.get(1, 0)}")
    print(f"    Tier 2 (popular):              {tier_counts.get(2, 0)}")
    print(f"    Tier 3 (esoteric):             {tier_counts.get(3, 0)}")
    print(f"    Tier 4 (long-tail):            {tier_counts.get(4, 0)}")

    # How many need teach generation?
    needs_gen = sum(1 for t in v3.values() if not t.get('opsec_notes'))
    print(f"\n  Need teach generation:    {needs_gen} tools "
          f"({100*needs_gen//len(v3)}% of registry)")

    out_data = {
        'version': '3.0.0',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'source_registry_version': v2.get('version', 'unknown'),
        'tools': v3,
    }

    if write:
        OUT.write_text(json.dumps(out_data, indent=2, ensure_ascii=False))
        print(f"\n  ✓ wrote {OUT}")
        print(f"  ✓ size: {OUT.stat().st_size / 1024:.1f} KB")
    else:
        print(f"\n  (dry-run — pass --write to actually emit {OUT.name})")


def main():
    parser = argparse.ArgumentParser(description='Expand registry to full BlackArch arsenal')
    parser.add_argument('--write', action='store_true', help='Actually write v3 file')
    args = parser.parse_args()

    print('=' * 70)
    print(' ERR0RS Registry Expansion — Phase 2.5')
    print('=' * 70 + '\n')

    if not RANKED.exists():
        print(f"  ✗ {RANKED} not found. Run the ranking step first.")
        sys.exit(1)
    if not BLACKARCH.exists():
        print(f"  ✗ {BLACKARCH} not found. Phoenix-OS missing.")
        sys.exit(1)

    build_v3(write=args.write)


if __name__ == '__main__':
    main()
