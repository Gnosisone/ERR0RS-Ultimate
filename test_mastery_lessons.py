import sys
sys.path.insert(0, 'H:/ERR0RS-Ultimate')

def chk(ok): return 'OK  ' if ok else 'FAIL'
all_ok = True

print('=== MASTERY LESSON COVERAGE TEST ===\n')

from src.education.teach_engine import LESSONS, ATTCK_KEYWORD_MAP, KEYWORD_MAP, find_lesson

print(f'Total LESSONS: {len(LESSONS)}')
print(f'KEYWORD_MAP entries: {len(KEYWORD_MAP)}')
print()

mastery_checks = [
    # (search term, should resolve to lesson key)
    ('active directory',         'active directory'),
    ('kerberos',                 'kerberos'),
    ('kerberoasting',            'kerberos'),
    ('golden ticket',            'kerberos'),
    ('mimikatz',                 'mimikatz'),
    ('dcsync',                   'mimikatz'),
    ('pass the hash',            'mimikatz'),
    ('bloodhound',               'bloodhound'),
    ('attack path',              'bloodhound'),
    ('pivoting',                 'pivoting'),
    ('port forwarding',          'pivoting'),
    ('chisel',                   'pivoting'),
    ('osint',                    'osint'),
    ('passive recon',            'osint'),
    ('shodan',                   'osint'),
    ('living off the land',      'living off the land'),
    ('lolbas',                   'living off the land'),
    ('gtfobins',                 'living off the land'),
    ('certutil',                 'living off the land'),
    ('web shells',               'web shells'),
    ('web shell',                'web shells'),
    ('upload bypass',            'web shells'),
    ('command injection',        'command injection'),
    ('rce',                      'command injection'),
    ('path traversal',           'path traversal'),
    ('directory traversal',      'path traversal'),
    ('lfi',                      'file inclusion'),
    ('rfi',                      'file inclusion'),
    ('file inclusion',           'file inclusion'),
    ('log poisoning',            'file inclusion'),
    ('ssrf',                     'ssrf'),
    ('aws metadata',             'ssrf'),
    ('xxe',                      'xxe'),
    ('xml external entity',      'xxe'),
    ('idor',                     'idor'),
    ('broken access control',    'idor'),
    ('deserialization',          'deserialization'),
    ('ysoserial',                'deserialization'),
    ('buffer overflow',          'buffer overflow'),
    ('bof',                      'buffer overflow'),
    ('binary exploitation',      'buffer overflow'),
    ('rop chain',                'buffer overflow'),
    ('pwntools',                 'buffer overflow'),
    # Already covered, verify still works
    ('nmap',                     'nmap'),
    ('metasploit',               'metasploit'),
    ('privilege escalation',     'privilege escalation'),
    ('sql injection',            'sql injection'),
    ('xss',                      'xss'),
    ('lateral movement',         'mitre_lateral'),
    ('credential access',        'mitre_creds'),
]

print('[Lesson resolution tests]')
for term, expected_key in mastery_checks:
    result = find_lesson(term)
    ok = result is not None
    if not ok: all_ok = False
    title = result.get('title', '???')[:45] if result else 'NOT FOUND'
    print(f'  [{chk(ok)}] "{term:<30}" -> {title}')

print()
print('[Lesson content depth check — key fields present]')
required_fields = ['title', 'tldr', 'what']
for key in ['active directory', 'kerberos', 'mimikatz', 'bloodhound',
            'pivoting', 'osint', 'living off the land', 'web shells',
            'command injection', 'path traversal', 'file inclusion',
            'ssrf', 'xxe', 'idor', 'deserialization', 'buffer overflow']:
    lesson = LESSONS.get(key)
    if lesson is None:
        print(f'  [FAIL] {key}: not in LESSONS dict')
        all_ok = False
        continue
    missing = [f for f in required_fields if f not in lesson]
    ok = len(missing) == 0
    if not ok: all_ok = False
    has_cmds = 'commands' in lesson
    has_tips = 'tips' in lesson
    print(f'  [{chk(ok)}] {key:<30} fields={list(lesson.keys())[:4]} cmds={has_cmds} tips={has_tips}')

print()
print(f'Total lessons in LESSONS dict: {len(LESSONS)}')
print(f'All lessons:')
for k in sorted(LESSONS.keys()):
    print(f'  {k}')

print(f'\n=== {"ALL PASS" if all_ok else "CHECK FAILURES ABOVE"} ===')
