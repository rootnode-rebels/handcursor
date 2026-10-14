import sys
import types

# Ensure matplotlib import in MediaPipe's unused drawing_utils succeeds without bloat
class _DummyModule(types.ModuleType):
    def __getattr__(self, name):
        return _DummyModule(name)
    def __call__(self, *args, **kwargs):
        return _DummyModule("dummy")

for _mod in ("matplotlib", "matplotlib.pyplot"):
    if _mod not in sys.modules:
        try:
            __import__(_mod)
        except ImportError:
            sys.modules[_mod] = _DummyModule(_mod)

from app_desktop import main

if __name__ == '__main__':
    main()
