import sys
import types

# Provide lightweight stubs for matplotlib if missing (MediaPipe drawing_utils imports it unconditionally)
if "matplotlib" not in sys.modules:
    try:
        import matplotlib
        import matplotlib.pyplot
    except ImportError:
        class _PyplotStub(types.ModuleType):
            def __getattr__(self, name):
                return lambda *a, **kw: None
        _mat = types.ModuleType("matplotlib")
        _mat.__path__ = []
        _plt = _PyplotStub("matplotlib.pyplot")
        sys.modules["matplotlib"] = _mat
        sys.modules["matplotlib.pyplot"] = _plt


from app_desktop import main

if __name__ == '__main__':
    main()
