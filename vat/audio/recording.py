import wave
from PySide6.QtCore import QObject, Signal
from . import pyaudio, PYAUDIO_AVAILABLE

# Archival capture format. Language-documentation archives follow the IASA
# TC-04 preservation standard: uncompressed linear PCM WAV, 48 kHz, 24-bit.
# We capture 24-bit when the input device supports it and fall back to 16-bit
# at the same 48 kHz rate (PARADISEC's accepted minimal field-capture depth)
# when it does not, so recording never fails on hardware lacking 24-bit input.
SAMPLE_RATE = 48000
CHANNELS = 1
FRAMES_PER_BUFFER = 1024

class AudioRecordingWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def __init__(self, wav_path: str):
        super().__init__()
        self.wav_path = wav_path
        self.should_stop = False
        self.frames = []

    def _open_stream(self, p):
        """Open an input stream, preferring 24-bit and falling back to 16-bit.

        Returns (stream, sample_width_bytes)."""
        try:
            stream = p.open(
                format=pyaudio.paInt24,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=FRAMES_PER_BUFFER,
            )
            return stream, 3
        except Exception:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=FRAMES_PER_BUFFER,
            )
            return stream, 2

    def run(self):
        if not PYAUDIO_AVAILABLE:
            self.error.emit("PyAudio is not available")
            self.finished.emit()
            return
        p = None
        stream = None
        try:
            p = pyaudio.PyAudio()
            stream, sample_width = self._open_stream(p)
            while not self.should_stop:
                data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                self.frames.append(data)
            stream.stop_stream()
            stream.close()
            stream = None
            p.terminate()
            p = None
            if self.frames:
                wf = wave.open(self.wav_path, 'wb')
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(sample_width)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(b''.join(self.frames))
                wf.close()
        except Exception as e:
            self.error.emit(f"Recording failed: {e}")
        finally:
            try:
                if stream is not None:
                    stream.stop_stream()
                    stream.close()
            except Exception:
                pass
            try:
                if p is not None:
                    p.terminate()
            except Exception:
                pass
            self.finished.emit()

    def stop(self):
        self.should_stop = True
