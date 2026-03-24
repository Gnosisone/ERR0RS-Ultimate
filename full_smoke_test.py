import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

print("=" * 60)
print("ERR0RS ULTIMATE — FULL LAUNCH SMOKE TEST")
print("=" * 60)

import importlib.util
ok, fail = [], []

tests = [
    ('language_layer',    'src.core.language_layer',       'classify_command'),
    ('language_v2',       'src.core.language_expansion_v2','fuzzy_match_tool'),
    ('smart_wizard',      'src.core.smart_wizard',         'detect_wizard'),
    ('campaign_manager',  'src.orchestration.campaign_manager', 'campaign_mgr'),
    ('auto_killchain',    'src.orchestration.auto_killchain',   'AutoKillChain'),
    ('pro_reporter',      'src.reporting.pro_reporter',         'ProReporter'),
    ('cred_engine',       'src.tools.credentials.credential_engine', 'cred_engine'),
    ('se_engine',         'src.tools.se_engine.se_engine',      'SocialEngineeringEngine'),
    ('ai_threat',         'src.tools.threat.ai_threat_engine',  'handle_ai_threat_command'),
    ('teach_engine',      'src.education.teach_engine',         'handle_teach_request'),
    ('run_postex',        'src.tools.postex.postex_module',      'run_postex'),
    ('run_wireless',      'src.tools.wireless.wireless_module',  'run_wireless'),
    ('run_social',        'src.tools.social.social_module',      'run_social'),
    ('cloud_module',      'src.tools.cloud.cloud_module',        None),
    ('ctf_solver',        'src.tools.ctf.ctf_solver',            None),
    ('opsec_module',      'src.tools.opsec.opsec_module',        None),
]

for name, mod_path, attr in tests:
    try:
        mod = importlib.import_module(mod_path)
        if attr:
            getattr(mod, attr)
        ok.append(name)
        print(f'  OK   {name}')
    except Exception as e:
        fail.append((name, str(e)[:80]))
        print(f'  FAIL {name}: {str(e)[:80]}')

print(f'\n  TOTAL: {len(ok)}/{len(ok)+len(fail)} modules OK')
if fail:
    print('\n  FAILURES:')
    for n, e in fail:
        print(f'    {n}: {e}')
