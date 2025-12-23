# Audio package: expose PyAudio availability to UI
try:
    import pyaudio  # type: ignore
    PYAUDIO_AVAILABLE = True
except (ImportError, OSError):
    PYAUDIO_AVAILABLE = False
    pyaudio = None  # type: ignore

__all__ = ["PYAUDIO_AVAILABLE", "pyaudio"]
