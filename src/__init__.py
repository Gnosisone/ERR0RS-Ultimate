# ERR0RS ULTIMATE - src package
# Redirect education imports to education_new (teach_engine.py locked by Defender)
import sys as _sys
import importlib.util as _ilu
import os as _os

_edu_new = _os.path.join(_os.path.dirname(__file__), 'education_new')

if _os.path.isdir(_edu_new) and 'src.education' not in _sys.modules:
    # Pre-register BOTH modules in sys.modules BEFORE exec_module runs.
    # This prevents a ModuleNotFoundError race if anything in the exec chain
    # (or a concurrent import of src.ai.knowledge) tries to import
    # src.education.knowledge_base before we finish loading src.education.
    _spec = _ilu.spec_from_file_location(
        'src.education',
        _os.path.join(_edu_new, '__init__.py'),
        submodule_search_locations=[_edu_new]
    )
    _mod = _ilu.module_from_spec(_spec)

    _te_spec = _ilu.spec_from_file_location(
        'src.education.teach_engine',
        _os.path.join(_edu_new, 'teach_engine.py')
    )
    _te_mod = _ilu.module_from_spec(_te_spec)

    _kb_path = _os.path.join(_edu_new, 'knowledge_base.py')
    if _os.path.isfile(_kb_path):
        _kb_spec = _ilu.spec_from_file_location('src.education.knowledge_base', _kb_path)
        _kb_mod = _ilu.module_from_spec(_kb_spec)
    else:
        # Stub so imports never fail even if the file is absent
        import types as _types
        _kb_mod = _types.ModuleType('src.education.knowledge_base')

    # Register everything atomically before any exec_module call
    _sys.modules['src.education']               = _mod
    _sys.modules['src.education.teach_engine']  = _te_mod
    _sys.modules['src.education.knowledge_base'] = _kb_mod

    # Now safe to execute — no import can race us
    _spec.loader.exec_module(_mod)
    _te_spec.loader.exec_module(_te_mod)
    if hasattr(_kb_mod, '__spec__') and _kb_mod.__spec__ is not None:
        _kb_mod.__spec__.loader.exec_module(_kb_mod)
