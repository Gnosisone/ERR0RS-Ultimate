import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
import importlib

print("=" * 60)
print("ERR0RS ULTIMATE — PRE-COMMIT FINAL VALIDATION")
print("=" * 60)

tests = [
    ('language_layer',    'src.core.language_layer',                  'classify_command'),
    ('language_v2',       'src.core.language_expansion_v2',           'fuzzy_match_tool'),
    ('smart_wizard',      'src.core.smart_wizard',                    'detect_wizard'),
    ('campaign_manager',  'src.orchestration.campaign_manager',       'campaign_mgr'),
    ('auto_killchain',    'src.orchestration.auto_killchain',         'AutoKillChain'),
    ('pro_reporter',      'src.reporting.pro_reporter',               'ProReporter'),
    ('cred_engine',       'src.tools.credentials.credential_engine',  'cred_engine'),
    ('se_engine',         'src.tools.se_engine.se_engine',            'SocialEngineeringEngine'),
    ('ai_threat',         'src.tools.threat.ai_threat_engine',        'handle_ai_threat_command'),
    ('teach_engine',      'src.education.teach_engine',               'handle_teach_request'),
    ('run_postex',        'src.tools.postex.postex_module',           'run_postex'),
    ('run_wireless',      'src.tools.wireless.wireless_module',       'run_wireless'),
    ('run_social',        'src.tools.social.social_module',           'run_social'),
    ('cloud_module',      'src.tools.cloud.cloud_module',             None),
    ('ctf_solver',        'src.tools.ctf.ctf_solver',                 None),
    ('opsec_module',      'src.tools.opsec.opsec_module',             None),
    ('flipper_evolution', 'src.tools.flipper.flipper_evolution',      'run_flipper_evolution'),
]

ok, fail = [], []
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

print(f'\n  RESULT: {len(ok)}/{len(ok)+len(fail)} modules OK')

# Test Flipper wizard trigger
print('\n  Wizard trigger tests:')
from src.core.smart_wizard import detect_wizard
for phrase in ['flipper', 'evolve flipper', 'make flipper happy', 'flipper evolution', 'arm flipper']:
    w = detect_wizard(phrase)
    status = 'OK' if w == 'flipper' else 'FAIL'
    print(f'    [{status}] detect_wizard({phrase!r}) -> {w}')

# Test language layer Flipper routing
print('\n  Language layer Flipper routing:')
from src.core.language_layer import classify_command
for phrase in ['evolve my flipper', 'flipper zero', 'make flipper happy', 'sync flipper']:
    r = classify_command(phrase)
    cat = r.get('category','?') if isinstance(r, dict) else str(r)
    status = 'OK' if 'badusb' in str(r).lower() or 'flipper' in str(r).lower() else 'CHECK'
    print(f'    [{status}] classify({phrase!r}) -> {cat}')

print('\n  Pre-commit validation DONE.')
if fail:
    print(f'\n  FAILURES ({len(fail)}):')
    for n, e in fail:
        print(f'    {n}: {e}')
