import sys, ast
sys.path.insert(0, 'H:/ERR0RS-Ultimate')

with open('H:/ERR0RS-Ultimate/src/education/teach_engine.py', 'r', encoding='utf-8') as f:
    src = f.read()

# ── Remove the misplaced string entries from ATTCK_KEYWORD_MAP ────────────
# They landed between the last dict entry and the closing brace of ATTCK_KEYWORD_MAP
# Find the marker we added
marker = '  # ── Mastery additions ─────────────────────────────────────────────────'
marker_pos = src.find(marker)
if marker_pos == -1:
    print('ERROR: mastery additions marker not found')
    sys.exit(1)

# Find the closing brace of ATTCK_KEYWORD_MAP that comes AFTER our marker
closing_after = src.find('\n}\n', marker_pos)
if closing_after == -1:
    print('ERROR: closing brace after marker not found')
    sys.exit(1)

print(f'Marker at: {marker_pos}')
print(f'Closing at: {closing_after}')
print(f'Block to remove:\n{repr(src[marker_pos:marker_pos+100])}')

# Remove the misplaced block (marker through the closing brace, keep the brace)
new_src = src[:marker_pos] + src[closing_after:]

# ── Now find KEYWORD_MAP and insert the entries there correctly ─────────
# KEYWORD_MAP is a simple dict that maps strings to strings
# It ends with something like:  "ai attack": "atlas_prompt_injection",\n}
km_marker = 'KEYWORD_MAP = {'
km_pos = new_src.find(km_marker)
if km_pos == -1:
    print('ERROR: KEYWORD_MAP not found')
    sys.exit(1)

# Walk forward from KEYWORD_MAP to find its closing brace
# It's a simple dict of "string": "string" entries
# The closing brace is the first } that appears at the start of a line
# after a run of these simple entries
depth = 0
i = km_pos
while i < len(new_src):
    c = new_src[i]
    if c == '{': depth += 1
    elif c == '}':
        depth -= 1
        if depth == 0:
            km_close = i
            break
    i += 1

print(f'\nKEYWORD_MAP opens at {km_pos}, closes at {km_close}')
print(f'Context before close: {repr(new_src[km_close-80:km_close+5])}')

new_km_entries = '''
  # ── Mastery topic routing ─────────────────────────────────────────────
  "active directory":           "active directory",
  "active directory attacks":   "active directory",
  "ad attacks":                 "active directory",
  "domain enumeration":         "active directory",
  "domain controller":          "active directory",
  "responder":                  "active directory",
  "ntlm relay":                 "active directory",
  "llmnr poisoning":            "active directory",
  "impacket":                   "active directory",
  "kerberos":                   "kerberos",
  "kerberoasting":              "kerberos",
  "as-rep roasting":            "kerberos",
  "asrep roasting":             "kerberos",
  "golden ticket":              "kerberos",
  "silver ticket":              "kerberos",
  "pass the ticket":            "kerberos",
  "mimikatz":                   "mimikatz",
  "lsass dump":                 "mimikatz",
  "credential dump":            "mimikatz",
  "dcsync":                     "mimikatz",
  "secretsdump":                "mimikatz",
  "pass the hash":              "mimikatz",
  "pass-the-hash":              "mimikatz",
  "pth":                        "mimikatz",
  "bloodhound":                 "bloodhound",
  "sharphound":                 "bloodhound",
  "attack path":                "bloodhound",
  "pivoting":                   "pivoting",
  "pivot":                      "pivoting",
  "port forwarding":            "pivoting",
  "network pivoting":           "pivoting",
  "chisel":                     "pivoting",
  "ligolo":                     "pivoting",
  "proxychains":                "pivoting",
  "osint":                      "osint",
  "open source intelligence":   "osint",
  "passive recon":              "osint",
  "footprinting":               "osint",
  "shodan":                     "osint",
  "living off the land":        "living off the land",
  "lotl":                       "living off the land",
  "lolbas":                     "living off the land",
  "gtfobins":                   "living off the land",
  "certutil":                   "living off the land",
  "mshta":                      "living off the land",
  "regsvr32":                   "living off the land",
  "web shells":                 "web shells",
  "web shell":                  "web shells",
  "file upload":                "web shells",
  "upload bypass":              "web shells",
  "weevely":                    "web shells",
  "command injection":          "command injection",
  "os command injection":       "command injection",
  "rce":                        "command injection",
  "remote code execution":      "command injection",
  "path traversal":             "path traversal",
  "directory traversal":        "path traversal",
  "lfi":                        "file inclusion",
  "rfi":                        "file inclusion",
  "file inclusion":             "file inclusion",
  "local file inclusion":       "file inclusion",
  "remote file inclusion":      "file inclusion",
  "log poisoning":              "file inclusion",
  "php wrapper":                "file inclusion",
  "ssrf":                       "ssrf",
  "server side request forgery":"ssrf",
  "aws metadata":               "ssrf",
  "imds":                       "ssrf",
  "xxe":                        "xxe",
  "xml external entity":        "xxe",
  "idor":                       "idor",
  "insecure direct object":     "idor",
  "broken access control":      "idor",
  "race condition":             "idor",
  "deserialization":            "deserialization",
  "insecure deserialization":   "deserialization",
  "ysoserial":                  "deserialization",
  "phpggc":                     "deserialization",
  "pickle":                     "deserialization",
  "buffer overflow":            "buffer overflow",
  "bof":                        "buffer overflow",
  "binary exploitation":        "buffer overflow",
  "rop chain":                  "buffer overflow",
  "pwntools":                   "buffer overflow",
  "ret2libc":                   "buffer overflow",
  "web application testing":    "burp suite",
  "active recon":               "nmap",
  "post exploitation":          "meterpreter",
  "post-exploitation":          "meterpreter",
  "persistence linux":          "mitre_persistence",
  "persistence windows":        "mitre_persistence",
  "cobalt strike":              "mitre_c2",'''

# Insert before the closing brace of KEYWORD_MAP
new_src = new_src[:km_close] + new_km_entries + '\n' + new_src[km_close:]

# ── Syntax check ──────────────────────────────────────────────────────────
try:
    ast.parse(new_src)
    print('\nSyntax check: PASS')
except SyntaxError as e:
    lines = new_src.split('\n')
    err_line = e.lineno - 1
    print(f'\nSYNTAX ERROR at line {e.lineno}: {e.msg}')
    for i in range(max(0, err_line-3), min(len(lines), err_line+4)):
        print(f'  {i+1:4}: {lines[i]}')
    sys.exit(1)

with open('H:/ERR0RS-Ultimate/src/education/teach_engine.py', 'w', encoding='utf-8') as f:
    f.write(new_src)

print(f'Written: {len(new_src.splitlines())} lines')
