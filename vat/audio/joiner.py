import os
import shutil
import tempfile
import threading
import numpy as np
from pydub import AudioSegment
from PySide6.QtCore import QObject, Signal
from typing import Optional
from vat.utils.fs_access import FolderAccessManager
from vat.audio.normalizer import Normalizer


class JoinWavsWorker(QObject):
    """Concatenates recordings into one WAV with a click between each.

    With a :class:`~vat.audio.normalizer.Normalizer` the recordings are first
    normalized one by one into a temporary folder and the *normalized copies*
    are joined — normalize before concatenating, so every item reaches the
    target level on its own and the clicks stay untouched. The originals are
    never modified; the temporary folder is removed afterwards.
    """

    finished = Signal()
    error = Signal(str)
    success = Signal(str)
    #: (phase, index, total, name) — phase is "normalize", "join" or "write".
    progress = Signal(str, int, int, str)
    canceled = Signal()

    def __init__(self, output_file: str = "", fs: Optional[FolderAccessManager] = None,
                 file_paths: Optional[list] = None, normalizer: Optional[Normalizer] = None):
        super().__init__()
        self.output_file = output_file
        self.fs = fs
        self.file_paths = file_paths or []
        self.normalizer = normalizer
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """Stop as soon as possible; no output file is written after this."""
        self._cancel.set()
        if self.normalizer is not None:
            self.normalizer.cancel()

    def generate_click_sound_pydub(self, duration_ms: int, freq: int, rate: int):
        t = np.linspace(0, duration_ms / 1000, int(rate * duration_ms / 1000), endpoint=False)
        sine_wave = np.sin(2 * np.pi * freq * t)
        decay = np.linspace(1, 0, len(sine_wave))
        click_data = sine_wave * decay
        click_data = (click_data * 0.5 * (2**15 - 1)).astype(np.int16).tobytes()
        return AudioSegment(
            data=click_data,
            sample_width=2,
            frame_rate=rate,
            channels=1
        )

    def _normalized_copies(self, wav_files: list, tmpdir: str) -> list:
        """Normalize every recording into tmpdir, in order; raise on failure."""
        # An index prefix keeps the join order and avoids clashes between
        # same-named recordings from different folders (e.g. images/).
        pairs = [
            (path, os.path.join(tmpdir, f"{i:04d}_{os.path.basename(path)}"))
            for i, path in enumerate(wav_files)
        ]
        results = self.normalizer.normalize_many(
            pairs,
            progress=lambda i, n, name: self.progress.emit("normalize", i, n, name),
        )
        if self.normalizer.canceled or any(r.canceled for r in results):
            raise _Canceled()
        failed = [r for r in results if not r.ok]
        if failed:
            raise RuntimeError(
                "Normalization failed for:\n" + "\n".join(f"{r.name}: {r.error}" for r in failed)
            )
        return [dst for _, dst in pairs]

    def run(self):
        tmpdir = None
        try:
            if self.file_paths:
                wav_paths = list(self.file_paths)
            else:
                if self.fs is None:
                    raise RuntimeError("No FolderAccessManager provided")
                wav_paths = self.fs.recordings_in()
            # Keep the FULL paths: re-deriving them from basenames breaks any
            # recording that lives in a subfolder (e.g. images/photo.jpg.wav).
            wav_files = sorted(wav_paths, key=lambda p: os.path.basename(p).lower())
            if self.normalizer is not None and wav_files:
                tmpdir = tempfile.mkdtemp(prefix="vat-normalize-")
                wav_files = self._normalized_copies(wav_files, tmpdir)
            # 48 kHz matches the archival capture rate (IASA TC-04). The joined
            # file is a derivative (per-item masters are the archival objects),
            # so we upscale to 32-bit rather than down to 24-bit: pydub cannot
            # emit true 24-bit (it upcasts 24-bit to 32-bit internally), and
            # 32-bit preserves the full 24-bit recordings losslessly instead of
            # truncating them to 16-bit. Both the 24-bit recordings and the
            # 16-bit-generated click/silence map to the same full-scale level at
            # 32-bit, so mixing them does not clip or shift levels.
            std_rate = 48000
            std_channels = 1
            std_sample_width = 4
            silence_segment = AudioSegment.silent(duration=500, frame_rate=std_rate)
            click_sound = self.generate_click_sound_pydub(duration_ms=5, freq=2000, rate=std_rate)
            click_segment = silence_segment + click_sound + silence_segment
            combined_audio = AudioSegment.empty()
            combined_audio = combined_audio.set_frame_rate(std_rate).set_channels(std_channels).set_sample_width(std_sample_width)
            total = len(wav_files)
            for i, file_path in enumerate(wav_files):
                if self._cancel.is_set():
                    raise _Canceled()
                self.progress.emit("join", i, total, os.path.basename(file_path))
                audio = AudioSegment.from_file(file_path, format="wav")
                if audio.frame_rate != std_rate:
                    audio = audio.set_frame_rate(std_rate)
                if audio.channels != std_channels:
                    audio = audio.set_channels(std_channels)
                if audio.sample_width != std_sample_width:
                    audio = audio.set_sample_width(std_sample_width)
                combined_audio += audio
                if i < len(wav_files) - 1:
                    combined_audio += click_segment
            if self._cancel.is_set():
                raise _Canceled()
            self.progress.emit("write", total, total, os.path.basename(self.output_file))
            combined_audio.export(self.output_file, format="wav")
            self.success.emit(self.output_file)
        except _Canceled:
            self.canceled.emit()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)
            self.finished.emit()


class _Canceled(Exception):
    """Internal: unwinds run() after a cancel without reporting an error."""
