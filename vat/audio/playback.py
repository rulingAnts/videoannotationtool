import wave
from PySide6.QtCore import QObject, Signal
from . import pyaudio, PYAUDIO_AVAILABLE

class AudioPlaybackWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def __init__(self, wav_path: str):
        super().__init__()
        self.wav_path = wav_path
        self.should_stop = False

    def run(self):
        if not PYAUDIO_AVAILABLE:
            self.error.emit("PyAudio is not available")
            self.finished.emit()
            return
        try:
            p = pyaudio.PyAudio()
            wf = wave.open(self.wav_path, 'rb')
            stream = p.open(
                format=p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True
            )
            data = wf.readframes(1024)
            while data and not self.should_stop:
                stream.write(data)
                data = wf.readframes(1024)
            stream.stop_stream()
            stream.close()
            p.terminate()
            wf.close()
        except Exception as e:
            self.error.emit(f"Audio playback failed: {e}")
        finally:
            self.finished.emit()

    def stop(self):
        self.should_stop = True
