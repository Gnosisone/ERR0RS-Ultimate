# ERR0RS ULTIMATE - src package
# Redirect education imports to education_new (teach_engine.py locked by Defender)
import sys as _sys
import importlib.util as _ilu
import os as _os

_edu_new = _os.path.join(_os.path.dirname(__file__), 'education_new')

if _os.path.isdir(_edu_new) and 'src.education' not in _sys.modules:
    # Pre-load education_new as src.education so all imports resolve correctly
    _spec = _ilu.spec_from_file_location(
        'src.education',
        _os.path.join(_edu_new, '__init__.py'),
        submodule_search_locations=[_edu_new]
    )
    _mod = _ilu.module_from_spec(_spec)
    _sys.modules['src.education'] = _mod
    _spec.loader.exec_module(_mod)

    _te_spec = _ilu.spec_from_file_location(
        'src.education.teach_engine',
        _os.path.join(_edu_new, 'teach_engine.py')
    )
    _te_mod = _ilu.module_from_spec(_te_spec)
    _sys.modules['src.education.teach_engine'] = _te_mod
    _te_spec.loader.exec_module(_te_mod)
