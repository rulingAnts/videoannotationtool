import wave
from PySide6.QtCore import QObject, Signal
from . import pyaudio, PYAUDIO_AVAILABLE

class AudioRecordingWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def __init__(self, wav_path: str):
        super().__init__()
        self.wav_path = wav_path
        self.should_stop = False
        self.frames = []

    def run(self):
        if not PYAUDIO_AVAILABLE:
            self.error.emit("PyAudio is not available")
            self.finished.emit()
            return
        try:
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=44100,
                input=True,
                frames_per_buffer=1024
            )
            while not self.should_stop:
                data = stream.read(1024, exception_on_overflow=False)
                self.frames.append(data)
            stream.stop_stream()
            stream.close()
            p.terminate()
            if self.frames:
                wf = wave.open(self.wav_path, 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(44100)
                wf.writeframes(b''.join(self.frames))
                wf.close()
        except Exception as e:
            self.error.emit(f"Recording failed: {e}")
        finally:
            self.finished.emit()

    def stop(self):
        self.should_stop = True
