# ERR0RS ULTIMATE — src package init
#
# Historical context: on the original Windows development host, Windows
# Defender repeatedly quarantined src/education/teach_engine.py because it
# flags the offline pentest lesson content as malware. A parallel copy was
# placed in src/education_new/ and an aliasing shim mapped the historical
# import name `src.education` onto it so existing `from src.education...`
# call sites kept working. On Kali/Linux there is no Defender; the alias is
# kept purely for backward compatibility with the call sites that still
# import `src.education.teach_engine` / `src.education.knowledge_base`.
#
# The alias is implemented below as a PEP 451 meta-path finder rather than an
# eager copy into sys.modules, so the alias and native names always resolve
# to ONE module object regardless of which name is imported first. See the
# detailed rationale on the finder class itself.
import sys as _sys
import os as _os

_edu_new_dir = _os.path.join(_os.path.dirname(__file__), 'education_new')

# ── Education alias via meta-path finder (single-identity guarantee) ────────
# The previous approach eagerly imported src.education_new at `src` import
# time and copied the module objects into sys.modules under src.education*.
# That worked ONLY if `import src` ran before any call site imported the
# engine under its native src.education_new name. In the real launcher boot
# order it did not: education_new/__init__.py imports teach_engine (load #1),
# then a call site's `from src.education.teach_engine import ...` re-executed
# the module under the alias name (load #2). Measured: the two names resolved
# to two distinct module objects — a split-state hazard and the doubled
# "lessons loaded" boot lines.
#
# The correct, order-independent fix is a PEP 451 meta-path finder. It maps
# any import of `src.education` or `src.education.<sub>` onto the corresponding
# already-resolved `src.education_new[.<sub>]` module OBJECT. Because Python
# consults sys.modules first and our finder hands back the identical object,
# both names share one identity no matter who imports which name first, and
# the module body executes exactly once.
if _os.path.isdir(_edu_new_dir) and 'src.education' not in _sys.modules:
    import importlib as _il
    import importlib.abc as _ilabc
    import importlib.util as _ilutil

    class _EducationAliasFinder(_ilabc.MetaPathFinder, _ilabc.Loader):
        """Aliases src.education[.*] -> src.education_new[.*], one identity."""
        _PREFIX = 'src.education'
        _TARGET = 'src.education_new'

        def _target_name(self, fullname):
            # src.education            -> src.education_new
            # src.education.teach_engine -> src.education_new.teach_engine
            return self._TARGET + fullname[len(self._PREFIX):]

        def find_spec(self, fullname, path=None, target=None):
            # Only handle the exact package and its submodules; never anything
            # under src.education_new itself (avoids infinite recursion).
            if fullname != self._PREFIX and not fullname.startswith(self._PREFIX + '.'):
                return None
            if fullname.startswith(self._TARGET):
                return None
            return _ilutil.spec_from_loader(fullname, self)

        def create_module(self, spec):
            # Resolve (importing if needed) the real education_new module and
            # return that SAME object as the alias module. Single identity.
            target = self._target_name(spec.name)
            try:
                mod = _il.import_module(target)
            except Exception:
                return None  # fall through to other finders / real package
            _sys.modules[spec.name] = mod
            return mod

        def exec_module(self, module):
            # The module body already executed under its native name during
            # create_module's import_module(); nothing to re-execute here.
            return None

    # Install at the FRONT so it wins before the default path finder ever
    # tries to load a second copy of src/education/teach_engine.py.
    _sys.meta_path.insert(0, _EducationAliasFinder())
