import sys, os, ast, json, re
sys.path.insert(0, 'H:/ERR0RS-Ultimate')

B = 'H:/ERR0RS-Ultimate'
ok = True

print('=== ERR0RS PRE-FLIGHT CHECK ===\n')

# ── 1. teach_engine redirect ──────────────────────────────────────────────
print('[1] teach_engine import')
try:
    from src.education.teach_engine import LESSONS, KEYWORD_MAP, find_lesson
    print(f'    OK  LESSONS={len(LESSONS)}  KEYWORD_MAP={len(KEYWORD_MAP)}')
    if len(LESSONS) < 40:
        print(f'    WARN: only {len(LESSONS)} lessons, expected 41')
        ok = False
except Exception as e:
    print(f'    FAIL: {e}')
    ok = False

# ── 2. Blue team ──────────────────────────────────────────────────────────
print('[2] blue_team module')
try:
    from src.security.blue_team import auto_harden, generate_report, handle_blue_team_request
    r = auto_harden('port 3306 open')
    assert r['severity'] == 'CRITICAL', f'Expected CRITICAL got {r["severity"]}'
    print(f'    OK  auto_harden works  severity={r["severity"]}')
except Exception as e:
    print(f'    FAIL: {e}'); ok = False

# ── 3. Payload studio ─────────────────────────────────────────────────────
print('[3] payload_studio snippets')
try:
    from src.tools.payload_studio.snippets import SNIPPETS, get_payload
    total = sum(len(v) for v in SNIPPETS.values())
    r = get_payload('linux_rev_shell', ip='1.2.3.4', port=4444)
    assert '1.2.3.4' in r
    print(f'    OK  {total} cards  get_payload works')
except Exception as e:
    print(f'    FAIL: {e}'); ok = False

# ── 4. RocketGod ──────────────────────────────────────────────────────────
print('[4] rocketgod')
try:
    from src.tools.rocketgod.rocketgod_kb import handle_rocketgod_request
    r = handle_rocketgod_request({'action': 'jammer_modes'})
    assert len(r.get('modes', {})) == 14
    print(f'    OK  {len(r["modes"])} jammer modes')
except Exception as e:
    print(f'    FAIL: {e}'); ok = False

# ── 5. BadUSB ─────────────────────────────────────────────────────────────
print('[5] badusb engine')
try:
    from src.tools.badusb import BADUSB_AVAILABLE, nlp_to_flipper
    assert BADUSB_AVAILABLE, 'BADUSB_AVAILABLE is False'
    r = nlp_to_flipper('open terminal and run ping test')
    assert 'stdout' in r
    print(f'    OK  BADUSB_AVAILABLE=True  nlp works')
except Exception as e:
    print(f'    FAIL: {e}'); ok = False

# ── 6. Language layer ─────────────────────────────────────────────────────
print('[6] language_layer')
try:
    from src.core.language_layer import classify_command
    r = classify_command('teach me kerberoasting')
    print(f'    OK  classify_command("teach me kerberoasting") = {r!r}')
except Exception as e:
    print(f'    FAIL: {e}'); ok = False

# ── 7. Launcher endpoints ─────────────────────────────────────────────────
print('[7] launcher endpoints')
launcher = open(f'{B}/src/ui/errorz_launcher.py', encoding='utf-8').read()
checks = [
    ('blue_team import',  'from src.security.blue_team import'),
    ('/api/blue_team',    '/api/blue_team'),
    ('/api/harden',       '/api/harden'),
    ('/api/report',       '/api/report'),
    ('SOC harden_cmd',    'harden_cmd'),
]
for name, pat in checks:
    if pat in launcher:
        print(f'    OK  {name}')
    else:
        print(f'    MISS {name}'); ok = False

# ── 8. HTML files ─────────────────────────────────────────────────────────
print('[8] HTML files')
for path, marker, label in [
    (f'{B}/src/ui/web/index.html',          'const SNIPPETS', 'index.html'),
    (f'{B}/src/ui/web/payload_studio.html', 'const SNIPPETS', 'payload_studio.html'),
]:
    if os.path.exists(path):
        content = open(path, encoding='utf-8').read()
        found = marker in content
        status = 'OK ' if found else 'MISS'
        print(f'    {status} {label} — const SNIPPETS={found}')
        if not found: ok = False
    else:
        print(f'    MISS {label} not found'); ok = False

# ── 9. Key lesson coverage ────────────────────────────────────────────────
print('[9] mastery lesson coverage')
mastery = [
    'active directory','kerberos','mimikatz','bloodhound',
    'pivoting','osint','living off the land','web shells',
    'command injection','path traversal','file inclusion',
    'ssrf','xxe','idor','deserialization','buffer overflow',
    'kerberoasting','golden ticket','dcsync','lfi','rfi','rce','bof',
]
missing = [t for t in mastery if not find_lesson(t)]
if missing:
    print(f'    MISS {len(missing)} topics: {missing}'); ok = False
else:
    print(f'    OK  all {len(mastery)} mastery topics resolve')

print(f'\n=== {"ALL SYSTEMS GO" if ok else "ISSUES FOUND - see above"} ===')
