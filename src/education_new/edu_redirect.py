import os, sys

# Monkey-patch: make 'src.education' resolve to 'src.education_new'
# This is inserted at the top of errorz_launcher.py startup
sys.path.insert(0, 'H:/ERR0RS-Ultimate')

import importlib, types

# Load education_new as a module
spec = importlib.util.spec_from_file_location(
    'src.education',
    'H:/ERR0RS-Ultimate/src/education_new/__init__.py',
    submodule_search_locations=['H:/ERR0RS-Ultimate/src/education_new']
)
edu_mod = importlib.util.module_from_spec(spec)
sys.modules['src.education'] = edu_mod
spec.loader.exec_module(edu_mod)

# Load teach_engine from education_new
te_spec = importlib.util.spec_from_file_location(
    'src.education.teach_engine',
    'H:/ERR0RS-Ultimate/src/education_new/teach_engine.py'
)
te_mod = importlib.util.module_from_spec(te_spec)
sys.modules['src.education.teach_engine'] = te_mod
te_spec.loader.exec_module(te_mod)

print(f'[ERR0RS] Education module redirected: {len(te_mod.LESSONS)} lessons loaded')
