import sys
sys.path.insert(0, '.')
import io
from contextlib import redirect_stderr, redirect_stdout

# Test all 3 previously broken imports
tests = [
    ('run_postex',   'from src.tools.postex.postex_module import run_postex'),
    ('run_wireless', 'from src.tools.wireless.wireless_module import run_wireless'),
    ('run_social',   'from src.tools.social.social_module import run_social'),
    ('PostExController',            'from src.tools.postex.postex_module import PostExController'),
    ('WirelessModule',              'from src.tools.wireless.wireless_module import WirelessModule'),
    ('SocialEngineeringController', 'from src.tools.social.social_module import SocialEngineeringController'),
]

ok = 0
for name, stmt in tests:
    try:
        exec(stmt)
        print(f'  OK   {name}')
        ok += 1
    except Exception as e:
        print(f'  FAIL {name}: {e}')

print(f'\nResult: {ok}/{len(tests)} passed')

# Quick smoke test — call each run_ wrapper
print('\n[Smoke tests]')
try:
    from src.tools.postex.postex_module import run_postex
    r = run_postex('whoami')
    print(f'  postex.whoami → status={r["status"]}, output={r["stdout"][:60]}')
except Exception as e:
    print(f'  postex smoke FAIL: {e}')

try:
    from src.tools.wireless.wireless_module import run_wireless
    r = run_wireless('monitor_on', {'interface': 'wlan0'})
    print(f'  wireless.monitor_on → status={r["status"]}')
except Exception as e:
    print(f'  wireless smoke FAIL: {e}')

try:
    from src.tools.social.social_module import run_social
    r = run_social('list_templates')
    print(f'  social.list_templates → status={r["status"]}')
except Exception as e:
    print(f'  social smoke FAIL: {e}')
