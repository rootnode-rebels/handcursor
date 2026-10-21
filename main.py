import sys
import types

# Ensure Per-Monitor DPI Awareness V2 is initialized before any GUI or graphics libraries load
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

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
