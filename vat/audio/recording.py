import wave
import os
import sys
import platform
import logging
import time
import audioop
import subprocess
from PySide6.QtCore import QObject, Signal
from . import pyaudio, PYAUDIO_AVAILABLE
from vat.utils.resources import resolve_ff_tools

# Dedicated recording diagnostics logger (append-only)
_REC_LOG_PATH = os.path.expanduser("~/.videonnotation.log")
_rec_logger = logging.getLogger("vat.audio.recording")
_rec_logger.setLevel(logging.DEBUG)
if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', '') == _REC_LOG_PATH for h in _rec_logger.handlers):
    try:
        fh = logging.FileHandler(_REC_LOG_PATH, mode='a', encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        _rec_logger.addHandler(fh)
        _rec_logger.propagate = False
        _rec_logger.debug("Recording diagnostics logger initialized at %s", _REC_LOG_PATH)
    except Exception as e:
        # Fall back to stderr if file cannot be opened
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        _rec_logger.addHandler(sh)
        _rec_logger.warning("Failed to open diagnostics log file %s: %s", _REC_LOG_PATH, e)

class AudioRecordingWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def __init__(self, wav_path: str):
        super().__init__()
        self.wav_path = wav_path
        self.should_stop = False
        self.frames = []
        self._silent_chunks = 0
        self._total_chunks = 0

    def run(self):
        _rec_logger.info("=== Recording session start ===")
        _rec_logger.info("Target WAV path: %s", self.wav_path)
        _rec_logger.info("Python: %s @ %s", sys.version.split()[0], sys.executable)
        _rec_logger.info("Platform: %s, machine: %s, frozen: %s", sys.platform, platform.machine(), getattr(sys, 'frozen', False))
        if not PYAUDIO_AVAILABLE:
            _rec_logger.error("PyAudio is not available (import failed or missing library)")
            self.error.emit("PyAudio is not available")
            self.finished.emit()
            return
        try:
            # Resolve and log ffmpeg/ffprobe availability
            ff = resolve_ff_tools()
            _rec_logger.info("FFmpeg resolved: %s (origin=%s)", ff['ffmpeg'], ff['ffmpeg_origin'])
            _rec_logger.info("FFprobe resolved: %s (origin=%s)", ff['ffprobe'], ff['ffprobe_origin'])
            for tool_name in ('ffmpeg', 'ffprobe'):
                tool_path = ff.get(tool_name)
                if tool_path and os.path.exists(tool_path):
                    try:
                        proc = subprocess.run([tool_path, '-version'], capture_output=True, text=True, timeout=3)
                        _rec_logger.debug("%s -version exit=%s", tool_name, proc.returncode)
                        _rec_logger.debug("%s stdout:\n%s", tool_name, (proc.stdout or '').strip())
                        _rec_logger.debug("%s stderr:\n%s", tool_name, (proc.stderr or '').strip())
                    except Exception as e:
                        _rec_logger.warning("Failed to run %s -version: %s", tool_name, e)

            # Initialize PyAudio and log devices/host APIs
            p = pyaudio.PyAudio()
            try:
                _rec_logger.info("PyAudio version: %s", getattr(pyaudio, '__version__', 'unknown'))
            except Exception:
                pass
            try:
                host_api_count = p.get_host_api_count()
                _rec_logger.info("Host API count: %d", host_api_count)
                for i in range(host_api_count):
                    info = p.get_host_api_info_by_index(i)
                    _rec_logger.debug("HostAPI[%d]: %s", i, info)
            except Exception as e:
                _rec_logger.warning("Unable to enumerate host APIs: %s", e)
            try:
                dev_count = p.get_device_count()
                _rec_logger.info("Input devices detected: %d", dev_count)
                for i in range(dev_count):
                    dinfo = p.get_device_info_by_index(i)
                    if dinfo.get('maxInputChannels', 0) > 0:
                        _rec_logger.debug("InputDevice[%d]: name=%s, channels=%s, defaultSR=%s, hostApi=%s", i, dinfo.get('name'), dinfo.get('maxInputChannels'), dinfo.get('defaultSampleRate'), dinfo.get('hostApi'))
            except Exception as e:
                _rec_logger.warning("Unable to enumerate devices: %s", e)
            try:
                default_info = p.get_default_input_device_info()
                _rec_logger.info("Default input device: %s", default_info)
            except Exception as e:
                default_info = None
                _rec_logger.error("No default input device info: %s", e)

            # Open input stream (explicitly target default input device index)
            try:
                default_idx = p.get_default_input_device_info().get('index')
            except Exception:
                default_idx = None
            # Align stream rate with device default sample rate when available
            rate = 44100
            if default_info and 'defaultSampleRate' in default_info:
                try:
                    rate = int(float(default_info['defaultSampleRate']))
                    _rec_logger.info("Using device default sample rate: %d", rate)
                except Exception as e:
                    _rec_logger.warning("Failed to parse defaultSampleRate; using 44100: %s", e)
            _rec_logger.info(
                "Opening PyAudio stream: format=paInt16, channels=1, rate=%d, frames_per_buffer=1024, input=True, input_device_index=%s",
                rate,
                default_idx if default_idx is not None else 'auto'
            )
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=rate,
                input=True,
                input_device_index=default_idx if default_idx is not None else None,
                frames_per_buffer=1024
            )
            _rec_logger.info("Stream opened successfully")
            start_ts = time.time()
            while not self.should_stop:
                try:
                    data = stream.read(1024, exception_on_overflow=False)
                except Exception as e:
                    _rec_logger.error("stream.read error: %s", e)
                    break
                self._total_chunks += 1
                # Compute RMS to detect silence
                try:
                    rms = audioop.rms(data, 2)
                except Exception:
                    rms = 0
                if rms == 0:
                    self._silent_chunks += 1
                if self._total_chunks % 50 == 0:
                    _rec_logger.debug("Chunk #%d: len=%d bytes, rms=%d, silent_chunks=%d", self._total_chunks, len(data), rms, self._silent_chunks)
                self.frames.append(data)
            stream.stop_stream()
            stream.close()
            p.terminate()
            dur = time.time() - start_ts
            _rec_logger.info("Stream closed. Captured %d chunks over %.2fs", self._total_chunks, dur)
            if self._total_chunks:
                silent_pct = (self._silent_chunks / self._total_chunks) * 100.0
                _rec_logger.info("Silent chunks: %d/%d (%.1f%%)", self._silent_chunks, self._total_chunks, silent_pct)
            if self.frames:
                wf = wave.open(self.wav_path, 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(rate)
                wf.writeframes(b''.join(self.frames))
                wf.close()
                _rec_logger.info("Wrote WAV: %s (frames=%d, bytes=%d)", self.wav_path, len(self.frames), sum(len(f) for f in self.frames))
            else:
                _rec_logger.warning("No frames captured; WAV not written")
        except Exception as e:
            _rec_logger.exception("Recording failed: %s", e)
            self.error.emit(f"Recording failed: {e}")
        finally:
            _rec_logger.info("=== Recording session end ===")
            self.finished.emit()

    def stop(self):
        self.should_stop = True
        _rec_logger.info("Stop requested by UI")
