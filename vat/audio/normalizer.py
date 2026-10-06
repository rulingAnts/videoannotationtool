"""Audio normalization core (no Qt), ported from the Bulk Audio Normalizer.

This is the same FFmpeg processing the standalone Bulk Audio Normalizer
performs (``python_webview/backend/audio_processor.py`` in that project):

* **Peak mode** (``normMode="peak"``): measure the peak with ``volumedetect``
  and apply plain gain so the loudest sample reaches ``peakTargetDb``. By
  default it only boosts quiet files (``peakOnlyBoost``) and never applies a
  limiter or compressor, so amplitude relationships and headroom are kept —
  the right choice for acoustic analysis (Praat etc.).
* **LUFS mode** (``normMode="lufs"``): two-pass EBU R128 ``loudnorm`` to
  ``lufsTarget`` followed by a brick-wall ``alimiter`` at ``limiterLimit`` so
  nothing clips — consistent perceived loudness for listening.
* Optional **auto-trim** of leading/trailing silence (``autoTrim``), detected
  with ``silencedetect`` and padded by ``trimPadMs``.
* Output **bit depth** (``targetBitDepth``): ``"original"`` keeps the source
  format (24-bit stays 24-bit, float stays float), ``16`` always writes
  16-bit PCM, ``24`` writes 24-bit PCM without up-converting 16-bit sources.

The setting keys are deliberately identical to the Bulk Audio Normalizer's
so the two tools stay interchangeable and documentation applies to both.

Originals are never touched: every call writes a *new* file, and the app
only ever normalizes copies made for an export.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import struct
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from vat.utils.resources import resolve_ff_tools

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

#: Defaults match the Bulk Audio Normalizer's "high quality" defaults, except
#: ``targetBitDepth``: this app records 48 kHz / 24-bit archival masters, so an
#: export keeps the recording's own bit depth unless the user asks otherwise.
DEFAULT_SETTINGS: Dict[str, object] = {
    "normMode": "peak",            # "peak" | "lufs"
    "peakTargetDb": -2.0,          # peak mode: target peak (dBFS)
    "peakOnlyBoost": True,         # peak mode: never attenuate loud files
    "lufsTarget": -16.0,           # lufs mode: integrated loudness target
    "tpMargin": -1.0,              # lufs mode: true-peak target (dBTP)
    "limiterLimit": 0.97,          # lufs mode: alimiter ceiling, linear 0..1
    "fastNormalize": False,        # lufs mode: single pass instead of two
    "targetBitDepth": "original",  # "original" | 16 | 24
    "autoTrim": False,
    "trimPadMs": 800,
    "trimThresholdDb": -50,
    "trimMinDurationMs": 200,
    "trimMinFileMs": 800,
    "trimConservative": True,
    "trimHPF": True,
    "ffmpegThreads": 0,            # 0 = let FFmpeg decide
    "verboseLogs": False,
}

NORM_MODES = ("peak", "lufs")
BIT_DEPTHS = ("original", 16, 24)

#: ``volumedetect`` reports digital silence as about -91 dB (its 16-bit
#: histogram floor). Anything at or below this has no signal to normalize.
SILENCE_PEAK_DB = -90.0


def _as_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("1", "true", "yes", "on"):
            return True
        if v in ("0", "false", "no", "off"):
            return False
    return default


def _as_float(value, default: float) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    if f != f or f in (float("inf"), float("-inf")):
        return default
    return f


def _as_int(value, default: int, minimum: Optional[int] = None) -> int:
    try:
        i = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    if minimum is not None and i < minimum:
        return minimum
    return i


def normalize_settings(overrides: Optional[Dict] = None) -> Dict[str, object]:
    """Return a complete, type-checked settings dict.

    Unknown keys are dropped and bad values fall back to the default, so a
    hand-edited or outdated ``settings.json`` can never break an export.
    """
    src = overrides if isinstance(overrides, dict) else {}
    out: Dict[str, object] = dict(DEFAULT_SETTINGS)

    mode = str(src.get("normMode", out["normMode"])).strip().lower()
    out["normMode"] = mode if mode in NORM_MODES else DEFAULT_SETTINGS["normMode"]

    out["peakTargetDb"] = max(-60.0, min(0.0, _as_float(src.get("peakTargetDb"), DEFAULT_SETTINGS["peakTargetDb"])))
    out["peakOnlyBoost"] = _as_bool(src.get("peakOnlyBoost"), DEFAULT_SETTINGS["peakOnlyBoost"])
    out["lufsTarget"] = max(-70.0, min(-5.0, _as_float(src.get("lufsTarget"), DEFAULT_SETTINGS["lufsTarget"])))
    out["tpMargin"] = max(-9.0, min(0.0, _as_float(src.get("tpMargin"), DEFAULT_SETTINGS["tpMargin"])))
    out["limiterLimit"] = max(0.0625, min(1.0, _as_float(src.get("limiterLimit"), DEFAULT_SETTINGS["limiterLimit"])))
    out["fastNormalize"] = _as_bool(src.get("fastNormalize"), DEFAULT_SETTINGS["fastNormalize"])

    depth = src.get("targetBitDepth", out["targetBitDepth"])
    if isinstance(depth, str):
        d = depth.strip().lower()
        depth = "original" if d == "original" else _as_int(d, -1)
    elif isinstance(depth, (int, float)):
        depth = int(depth)
    out["targetBitDepth"] = depth if depth in BIT_DEPTHS else DEFAULT_SETTINGS["targetBitDepth"]

    out["autoTrim"] = _as_bool(src.get("autoTrim"), DEFAULT_SETTINGS["autoTrim"])
    out["trimPadMs"] = _as_int(src.get("trimPadMs"), DEFAULT_SETTINGS["trimPadMs"], minimum=0)
    out["trimThresholdDb"] = max(-120, min(0, _as_int(src.get("trimThresholdDb"), DEFAULT_SETTINGS["trimThresholdDb"])))
    out["trimMinDurationMs"] = _as_int(src.get("trimMinDurationMs"), DEFAULT_SETTINGS["trimMinDurationMs"], minimum=0)
    out["trimMinFileMs"] = _as_int(src.get("trimMinFileMs"), DEFAULT_SETTINGS["trimMinFileMs"], minimum=0)
    out["trimConservative"] = _as_bool(src.get("trimConservative"), DEFAULT_SETTINGS["trimConservative"])
    out["trimHPF"] = _as_bool(src.get("trimHPF"), DEFAULT_SETTINGS["trimHPF"])
    out["ffmpegThreads"] = _as_int(src.get("ffmpegThreads"), DEFAULT_SETTINGS["ffmpegThreads"], minimum=0)
    out["verboseLogs"] = _as_bool(src.get("verboseLogs"), DEFAULT_SETTINGS["verboseLogs"])
    return out


def describe_settings(settings: Dict[str, object]) -> str:
    """One line for logs and summaries, e.g. ``peak -2 dBFS, keep bit depth, no trim``."""
    s = normalize_settings(settings)
    if s["normMode"] == "lufs":
        core = f"LUFS {s['lufsTarget']:g}, TP {s['tpMargin']:g}, limiter {s['limiterLimit']:g}"
        if s["fastNormalize"]:
            core += ", single pass"
    else:
        core = f"peak {s['peakTargetDb']:g} dBFS"
        core += ", boost only" if s["peakOnlyBoost"] else ", boost or attenuate"
    depth = s["targetBitDepth"]
    depth_txt = "keep bit depth" if depth == "original" else f"{depth}-bit"
    trim_txt = f"trim (pad {s['trimPadMs']} ms)" if s["autoTrim"] else "no trim"
    return f"{core}, {depth_txt}, {trim_txt}"


# ---------------------------------------------------------------------------
# Errors and results
# ---------------------------------------------------------------------------

class NormalizeError(Exception):
    """FFmpeg is missing or a file could not be processed."""


class NormalizeCanceled(Exception):
    """Processing was canceled by the user; nothing more will be written."""


@dataclass
class NormalizeResult:
    """Outcome of normalizing one file."""
    source: str
    output: str
    ok: bool = False
    canceled: bool = False
    error: Optional[str] = None
    trimmed: bool = False
    gain_db: Optional[float] = None       # peak mode: gain applied
    measured: Dict[str, object] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return os.path.basename(self.source)


# ---------------------------------------------------------------------------
# FFmpeg helpers
# ---------------------------------------------------------------------------

def probe_tool(path: str, name: str = "ffmpeg", timeout: float = 20.0) -> Tuple[bool, str]:
    """Run ``<tool> -version`` and report ``(runs, detail)``.

    A file that exists is not enough: the Windows builds up to 2.4.1 shipped
    Chocolatey's *shim* launcher as ffmpeg.exe, which exits non-zero without
    a word on any PC that lacks the Chocolatey install it points at. The
    detail is the first version line when it runs, else the exit code and
    whatever the tool said.
    """
    try:
        proc = subprocess.Popen([path, "-version"], **_popen_kwargs())
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return False, f"{name} at {path} did not answer within {timeout:g}s"
    except OSError as e:
        return False, f"{name} at {path} cannot be started: {e}"
    text = (out or b"").decode("utf-8", errors="replace") + (err or b"").decode("utf-8", errors="replace")
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    if proc.returncode == 0 and first.lower().startswith(f"{name} version"):
        return True, first
    return False, (f"{name} at {path} does not run (exit code {proc.returncode}"
                   + (f": {first}" if first else ", no output") + ")")


def find_ff_tools() -> Tuple[str, str]:
    """Return ``(ffmpeg, ffprobe)`` paths that actually run, or raise.

    Prefers the bundled tools, then a system install on PATH. ``ffprobe``
    is optional at runtime (durations fall back to the WAV header), so only
    an unusable ``ffmpeg`` is fatal; the error names every candidate tried.
    """
    tools = resolve_ff_tools()
    candidates: List[str] = []
    for cand in (tools.get("ffmpeg"), shutil.which("ffmpeg")):
        if cand and os.path.exists(cand) and cand not in candidates:
            candidates.append(cand)
    problems: List[str] = []
    ffmpeg = ""
    for cand in candidates:
        ok, detail = probe_tool(cand, "ffmpeg")
        if ok:
            ffmpeg = cand
            logger.info(f"normalize: using {cand} ({detail})")
            break
        logger.warning(f"normalize: {detail}")
        problems.append(detail)
    if not ffmpeg:
        raise NormalizeError("ffmpeg not found" if not problems else "; ".join(problems))
    ffprobe = ""
    for cand in (tools.get("ffprobe"), shutil.which("ffprobe")):
        if cand and os.path.exists(cand):
            ok, detail = probe_tool(cand, "ffprobe")
            if ok:
                ffprobe = cand
                break
            logger.warning(f"normalize: {detail}")
    return ffmpeg, ffprobe


def _popen_kwargs() -> Dict[str, object]:
    """Popen options that are safe in a windowed (console-less) build.

    * All three standard handles are redirected: a PyInstaller ``console=False``
      build has no console, and an un-redirected handle makes CreateProcess
      fail with "The handle is invalid".
    * ``CREATE_NO_WINDOW`` keeps a console window from flashing on Windows
      for every FFmpeg pass.
    """
    kwargs: Dict[str, object] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
    }
    if os.name == "nt":
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    return kwargs


def get_wav_format_info(file_path: str) -> Optional[Dict[str, int]]:
    """Read the ``fmt `` chunk.

    Returns ``{"audioFormat": 1|3|65534, "channels": n, "sampleRate": hz,
    "bitsPerSample": n}`` or None when the file is not a RIFF/WAVE.
    """
    try:
        with open(file_path, "rb") as f:
            data = f.read(4096)
        if len(data) < 44 or data[0:4] != b"RIFF" or data[8:12] != b"WAVE":
            return None
        pos = 12
        while pos + 8 <= len(data):
            chunk_id = data[pos:pos + 4]
            chunk_size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
            if chunk_id == b"fmt " and pos + 24 <= len(data):
                audio_format, channels, sample_rate, _byte_rate, _align, bits = \
                    struct.unpack("<HHIIHH", data[pos + 8:pos + 24])
                return {
                    "audioFormat": audio_format,
                    "channels": channels,
                    "sampleRate": sample_rate,
                    "bitsPerSample": bits,
                }
            pos = pos + 8 + chunk_size + (chunk_size % 2)
        return None
    except Exception as e:  # pragma: no cover - defensive
        logger.debug(f"WAV format read failed for {file_path}: {e}")
        return None


def wav_header_duration(file_path: str) -> float:
    """Duration from the WAV header (0.0 when it cannot be read)."""
    try:
        with open(file_path, "rb") as f:
            data = f.read(512 * 1024)
        if len(data) < 44 or data[0:4] != b"RIFF" or data[8:12] != b"WAVE":
            return 0.0
        pos = 12
        byte_rate = 0
        data_size = 0
        while pos + 8 <= len(data):
            chunk_id = data[pos:pos + 4]
            chunk_size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
            if chunk_id == b"fmt " and pos + 20 <= len(data):
                byte_rate = struct.unpack("<I", data[pos + 16:pos + 20])[0]
            elif chunk_id == b"data":
                data_size = chunk_size
                break
            pos = pos + 8 + chunk_size + (chunk_size % 2)
        if byte_rate > 0 and data_size > 0:
            return data_size / byte_rate
    except Exception as e:  # pragma: no cover - defensive
        logger.debug(f"WAV header parse failed for {file_path}: {e}")
    return 0.0


#: SubFormat GUID of integer PCM inside a WAVE_FORMAT_EXTENSIBLE header.
_PCM_SUBFORMAT = b"\x01\x00\x00\x00\x00\x00\x10\x00\x80\x00\x00\xaa\x00\x38\x9b\x71"


def ensure_plain_pcm_header(path: str) -> bool:
    """Rewrite a WAVE_FORMAT_EXTENSIBLE integer-PCM file as classic WAVE_FORMAT_PCM.

    FFmpeg tags any PCM wider than 16 bits as EXTENSIBLE. The app's own
    recordings (written by the ``wave`` module) carry the classic tag, and
    ``wave`` before Python 3.12 (the Windows build runs 3.11) refuses the
    EXTENSIBLE one, so a normalized 24-bit export that was imported back
    would not play. Only the header changes: every sample is copied as is,
    and FFmpeg's extra chunks (LIST/INFO) are dropped. Float or more than
    two channels is left alone. Returns True when the file was rewritten.
    """
    try:
        file_size = os.path.getsize(path)
        with open(path, "rb") as f:
            head = f.read(12)
            if len(head) < 12 or head[:4] != b"RIFF" or head[8:12] != b"WAVE":
                return False
            fmt = None
            data_off = data_size = None
            pos = 12
            while pos + 8 <= file_size:
                f.seek(pos)
                hdr = f.read(8)
                if len(hdr) < 8:
                    break
                cid, size = hdr[:4], struct.unpack("<I", hdr[4:8])[0]
                if cid == b"fmt ":
                    fmt = f.read(size)
                elif cid == b"data":
                    data_off, data_size = pos + 8, size
                    break
                pos += 8 + size + (size % 2)
            if fmt is None or data_off is None or len(fmt) < 40:
                return False
            tag, channels, rate, byte_rate, block_align, bits = struct.unpack("<HHIIHH", fmt[:16])
            if tag != 0xFFFE or channels > 2 or fmt[24:40] != _PCM_SUBFORMAT:
                return False
            data_size = min(data_size, file_size - data_off)
            tmp = path + ".pcm-header.tmp"
            with open(tmp, "wb") as out:
                riff_size = 4 + (8 + 16) + (8 + data_size + (data_size % 2))
                out.write(b"RIFF" + struct.pack("<I", riff_size) + b"WAVE")
                out.write(b"fmt " + struct.pack("<IHHIIHH", 16, 1, channels, rate, byte_rate, block_align, bits))
                out.write(b"data" + struct.pack("<I", data_size))
                f.seek(data_off)
                remaining = data_size
                while remaining > 0:
                    chunk = f.read(min(1 << 20, remaining))
                    if not chunk:
                        break
                    out.write(chunk)
                    remaining -= len(chunk)
                if data_size % 2:
                    out.write(b"\x00")
        os.replace(tmp, path)
        return True
    except Exception as e:  # pragma: no cover - defensive: the file stays as FFmpeg wrote it
        logger.warning(f"could not rewrite WAV header of {path}: {e}")
        try:
            os.remove(path + ".pcm-header.tmp")
        except OSError:
            pass
        return False


def choose_output_codec(target_bit_depth, input_fmt: Optional[Dict[str, int]]) -> str:
    """Pick the PCM codec for ``targetBitDepth`` given the input's format."""
    if target_bit_depth == "original":
        if not input_fmt:
            return "pcm_s16le"
        bits = input_fmt.get("bitsPerSample", 0)
        fmt = input_fmt.get("audioFormat", 1)  # 1 = PCM, 3 = IEEE float
        if fmt == 3:
            return "pcm_f64le" if bits >= 64 else "pcm_f32le"
        if bits <= 8:
            return "pcm_u8"
        if bits <= 16:
            return "pcm_s16le"
        if bits <= 24:
            return "pcm_s24le"
        if bits <= 32:
            return "pcm_s32le"
        return "pcm_s16le"
    if target_bit_depth == 24:
        # Never up-convert a 16-bit source.
        if input_fmt and 0 < input_fmt.get("bitsPerSample", 0) <= 16:
            return "pcm_s16le"
        return "pcm_s24le"
    return "pcm_s16le"


def parse_loudnorm_json(stderr_text: str) -> Optional[Dict[str, object]]:
    """Find the JSON block ``loudnorm`` prints after its analysis pass.

    Searched from the end for a brace pair that parses and contains
    ``input_i``, because FFmpeg echoes the input file name earlier in stderr
    and a name may itself contain braces.
    """
    end = len(stderr_text)
    while True:
        start = stderr_text.rfind("{", 0, end)
        if start < 0:
            return None
        close = stderr_text.find("}", start)
        if close >= 0:
            try:
                parsed = json.loads(stderr_text[start:close + 1])
            except ValueError:
                parsed = None
            if isinstance(parsed, dict) and "input_i" in parsed:
                return parsed
        end = start


def ffmpeg_error_tail(stderr: Optional[bytes], lines: int = 3) -> str:
    """The last few non-empty stderr lines, joined, for an error message."""
    text = (stderr or b"").decode("utf-8", errors="replace")
    tail = [ln.strip() for ln in text.splitlines() if ln.strip()][-lines:]
    return " | ".join(tail) or "no error message"


def _finite(value) -> Optional[float]:
    """``loudnorm`` reports ``-inf`` for digital silence; treat that as absent."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


# ---------------------------------------------------------------------------
# Normalizer
# ---------------------------------------------------------------------------

class Normalizer:
    """Normalizes WAV files with FFmpeg; one instance per export job.

    Thread-safe cancellation: call :meth:`cancel` from any thread and the
    FFmpeg pass that is running is terminated, its partial output removed,
    and the current :meth:`normalize_file` returns a ``canceled`` result
    (``normalize_many`` stops after it).
    """

    def __init__(self, settings: Optional[Dict] = None,
                 tools: Optional[Tuple[str, str]] = None,
                 log: Optional[Callable[[str], None]] = None):
        self.settings = normalize_settings(settings)
        self.ffmpeg, self.ffprobe = tools if tools else find_ff_tools()
        self._log = log
        self._cancel = threading.Event()
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    # -- cancellation -------------------------------------------------------

    def cancel(self) -> None:
        self._cancel.set()
        with self._lock:
            proc = self._proc
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

    @property
    def canceled(self) -> bool:
        return self._cancel.is_set()

    # -- subprocess plumbing ---------------------------------------------------

    def _run(self, cmd: Sequence[str], timeout: Optional[float] = None) -> Tuple[int, bytes, bytes]:
        with self._lock:
            if self._cancel.is_set():
                raise NormalizeCanceled()
            proc = subprocess.Popen(list(cmd), **_popen_kwargs())
            self._proc = proc
        try:
            try:
                out, err = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, err = proc.communicate()
                raise NormalizeError(f"FFmpeg timed out after {timeout:g}s")
        finally:
            with self._lock:
                self._proc = None
        if self._cancel.is_set():
            raise NormalizeCanceled()
        if proc.returncode != 0:
            # Everything needed to diagnose a failure from the app log alone.
            logger.warning(
                "ffmpeg exit code %s for %s; stderr tail: %s",
                proc.returncode, subprocess.list2cmdline([str(c) for c in cmd]), ffmpeg_error_tail(err, 5),
            )
        return proc.returncode, out or b"", err or b""

    def _note(self, result: NormalizeResult, message: str) -> None:
        result.notes.append(message)
        if self._log:
            try:
                self._log(f"{result.name}: {message}")
            except Exception:
                pass
        logger.debug(f"normalize {result.name}: {message}")

    def _common_args(self) -> Tuple[List[str], List[str]]:
        verbosity = ["-v", "info"] if self.settings["verboseLogs"] else ["-hide_banner", "-v", "error"]
        threads = int(self.settings["ffmpegThreads"])
        thread_args = ["-threads", str(threads)] if threads > 0 else []
        return verbosity, thread_args

    # -- probing ----------------------------------------------------------------

    def duration_seconds(self, file_path: str) -> float:
        d = wav_header_duration(file_path)
        if d > 0:
            return d
        if not self.ffprobe:
            return 0.0
        try:
            rc, out, _ = self._run(
                [self.ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", file_path],
                timeout=30,
            )
            if rc == 0:
                return max(0.0, float(out.decode("utf-8", errors="ignore").strip() or 0.0))
        except NormalizeCanceled:
            raise
        except Exception as e:
            logger.debug(f"ffprobe duration failed for {file_path}: {e}")
        return 0.0

    def detect_voice_region(self, input_path: str, duration_sec: float,
                            result: NormalizeResult) -> Optional[Dict[str, float]]:
        """First/last non-silent instant via ``silencedetect`` (None = unknown)."""
        s = self.settings
        threshold_db = float(s["trimThresholdDb"])
        min_dur_sec = max(0.01, int(s["trimMinDurationMs"]) / 1000.0)
        if s["trimConservative"]:
            threshold_db = min(threshold_db, -60.0)
            min_dur_sec = max(min_dur_sec, 0.3)
        filters = []
        if s["trimHPF"]:
            filters.append("highpass=f=80")
        filters.append(f"silencedetect=n={threshold_db:g}dB:d={min_dur_sec:g}")
        self._note(result, f"trim detect: threshold={threshold_db:g} dB, min silence={min_dur_sec:g}s, "
                           f"HPF={'on' if s['trimHPF'] else 'off'}, conservative={'on' if s['trimConservative'] else 'off'}")
        rc, _, err = self._run(
            [self.ffmpeg, "-hide_banner", "-nostats", "-v", "info",
             "-i", input_path, "-af", ",".join(filters), "-f", "null", "-"],
            timeout=600,
        )
        if rc != 0:
            self._note(result, f"trim detect failed (exit code {rc}): {ffmpeg_error_tail(err)}")
            return None
        text = err.decode("utf-8", errors="ignore")
        starts = [float(m.group(1)) for m in re.finditer(r"silence_start: (-?[0-9.]+)", text)]
        ends = [float(m.group(1)) for m in re.finditer(r"silence_end: (-?[0-9.]+)", text)]
        intervals = [[starts[i], ends[i]] for i in range(min(len(starts), len(ends)))]
        if len(starts) > len(ends):           # file ends in silence
            intervals.append([starts[-1], duration_sec])
        intervals.sort()
        merged: List[List[float]] = []
        for start, end in intervals:
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        non_silent: List[List[float]] = []
        prev = 0.0
        for start, end in merged:
            if start > prev:
                non_silent.append([prev, start])
            prev = max(prev, end)
        if prev < duration_sec:
            non_silent.append([prev, duration_sec])
        if not non_silent:
            return None
        return {"start": non_silent[0][0], "end": non_silent[-1][1]}

    # -- the main entry point ---------------------------------------------------

    def normalize_file(self, input_path: str, output_path: str) -> NormalizeResult:
        """Write a normalized copy of ``input_path`` to ``output_path``.

        Never raises for a per-file problem: inspect ``result.ok``,
        ``result.canceled`` and ``result.error``. The output file is removed
        when the render fails or is canceled, so a half-written WAV is never
        left behind.
        """
        result = NormalizeResult(source=input_path, output=output_path)
        try:
            self._normalize(result)
            result.ok = True
        except NormalizeCanceled:
            result.canceled = True
            result.error = "canceled"
            self._discard(output_path)
        except NormalizeError as e:
            result.error = str(e)
            self._discard(output_path)
        except Exception as e:  # pragma: no cover - defensive
            logger.exception(f"normalize failed for {input_path}")
            result.error = f"{type(e).__name__}: {e}"
            self._discard(output_path)
        return result

    def normalize_many(self, pairs: Sequence[Tuple[str, str]],
                       progress: Optional[Callable[[int, int, str], None]] = None) -> List[NormalizeResult]:
        """Normalize ``(source, output)`` pairs in order; stops after a cancel.

        ``progress(index, total, name)`` is called before each file.
        """
        results: List[NormalizeResult] = []
        total = len(pairs)
        for i, (src, dst) in enumerate(pairs):
            if progress:
                progress(i, total, os.path.basename(src))
            if self._cancel.is_set():
                results.append(NormalizeResult(source=src, output=dst, canceled=True, error="canceled"))
                break
            r = self.normalize_file(src, dst)
            results.append(r)
            if r.canceled:
                break
        return results

    # -- internals --------------------------------------------------------------

    @staticmethod
    def _discard(path: str) -> None:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError:
            pass

    def _normalize(self, result: NormalizeResult) -> None:
        s = self.settings
        src, dst = result.source, result.output
        if not os.path.isfile(src):
            raise NormalizeError("source file is missing")
        out_dir = os.path.dirname(os.path.abspath(dst))
        os.makedirs(out_dir, exist_ok=True)

        duration = self.duration_seconds(src)
        input_fmt = get_wav_format_info(src)
        codec = choose_output_codec(s["targetBitDepth"], input_fmt)
        verbosity, thread_args = self._common_args()

        # 1) Trim detection -------------------------------------------------
        seek_start, seek_end = 0.0, duration
        if s["autoTrim"]:
            min_file_ms = int(s["trimMinFileMs"])
            if duration * 1000.0 >= min_file_ms and duration > 0:
                region = self.detect_voice_region(src, duration, result)
                if region:
                    pad = int(s["trimPadMs"]) / 1000.0
                    seek_start = max(0.0, region["start"] - pad)
                    seek_end = min(duration, region["end"] + pad)
                    if seek_start > 0 or seek_end < duration:
                        result.trimmed = True
                        self._note(result, f"trim: {seek_start:.3f}s – {seek_end:.3f}s of {duration:.3f}s")
                    else:
                        self._note(result, "trim: nothing to remove")
                else:
                    self._note(result, "trim skipped: no non-silent region detected")
            else:
                self._note(result, f"trim skipped: shorter than {min_file_ms} ms")
        seek_args: List[str] = []
        if seek_start > 0 or seek_end < duration:
            seek_args = ["-ss", f"{seek_start:.3f}", "-to", f"{seek_end:.3f}"]

        # 2) Analysis pass ------------------------------------------------------
        mode = s["normMode"]
        loudnorm_measured: Optional[Dict[str, float]] = None
        measured_peak_db: Optional[float] = None
        silent = False
        if mode == "lufs" and not s["fastNormalize"]:
            # loudnorm prints its measurement at FFmpeg's *info* level, so this
            # pass must not run at "-v error" or the JSON never appears and
            # the render silently degrades to single-pass (dynamic) mode.
            rc, _, err = self._run(
                [self.ffmpeg, "-hide_banner", "-nostats", "-v", "info"] + seek_args + ["-i", src] + thread_args +
                ["-af", f"loudnorm=I={s['lufsTarget']:g}:TP={s['tpMargin']:g}:LRA=11:print_format=json",
                 "-f", "null", "-"]
            )
            if rc != 0:
                raise NormalizeError(f"loudness analysis failed (exit code {rc}): {ffmpeg_error_tail(err)}")
            parsed = parse_loudnorm_json(err.decode("utf-8", errors="ignore"))
            if parsed:
                vals = {
                    "measured_I": _finite(parsed.get("input_i")),
                    "measured_LRA": _finite(parsed.get("input_lra")),
                    "measured_TP": _finite(parsed.get("input_tp")),
                    "measured_thresh": _finite(parsed.get("input_thresh")),
                    "offset": _finite(parsed.get("target_offset")),
                }
                if vals["measured_I"] is None:
                    # Everything sits below loudnorm's -70 LUFS gate (digital
                    # or near silence): there is no loudness to normalize, and
                    # dynamic loudnorm on such input renders full-scale noise.
                    silent = True
                elif all(v is not None for v in vals.values()):
                    loudnorm_measured = vals  # type: ignore[assignment]
                    result.measured.update(vals)
                    self._note(result, f"LUFS measured: I={vals['measured_I']:g} LUFS, "
                                       f"TP={vals['measured_TP']:g} dBTP, LRA={vals['measured_LRA']:g} LU (two-pass)")
                else:
                    self._note(result, "LUFS measured: incomplete measurement – single pass")
            else:
                self._note(result, "LUFS analysis: no measurement parsed – single pass")
        else:
            # Peak mode needs the peak; LUFS single-pass mode uses the same
            # cheap pass only to recognise digital silence (see above).
            rc, _, err = self._run(
                [self.ffmpeg, "-hide_banner", "-nostats", "-v", "info"] + seek_args + ["-i", src] + thread_args +
                ["-af", "volumedetect", "-f", "null", "-"]
            )
            if rc != 0:
                raise NormalizeError(f"peak analysis failed (exit code {rc}): {ffmpeg_error_tail(err)}")
            m = re.search(r"max_volume:\s*(-?[0-9.]+)\s*dB", err.decode("utf-8", errors="ignore"))
            if m:
                measured_peak_db = float(m.group(1))
                result.measured["max_volume_db"] = measured_peak_db
            if measured_peak_db is None or measured_peak_db <= SILENCE_PEAK_DB:
                silent = True

        # 3) Render pass --------------------------------------------------------
        filters: List[str] = []
        if silent:
            result.gain_db = 0.0
            self._note(result, "silent recording: left unchanged")
        elif mode == "lufs":
            base = f"loudnorm=I={s['lufsTarget']:g}:TP={s['tpMargin']:g}:LRA=11"
            if loudnorm_measured:
                base += (f":measured_I={loudnorm_measured['measured_I']:g}"
                         f":measured_LRA={loudnorm_measured['measured_LRA']:g}"
                         f":measured_TP={loudnorm_measured['measured_TP']:g}"
                         f":measured_thresh={loudnorm_measured['measured_thresh']:g}"
                         f":offset={loudnorm_measured['offset']:g}:linear=true")
            filters.append(base + ":print_format=summary")
            filters.append(f"alimiter=limit={s['limiterLimit']:g}:level_in=1.0:level_out=1.0")
        else:
            gain_db = 0.0
            if measured_peak_db is not None:
                ideal = float(s["peakTargetDb"]) - measured_peak_db
                gain_db = max(0.0, ideal) if s["peakOnlyBoost"] else ideal
                gain_db = max(-30.0, min(30.0, gain_db))
            result.gain_db = gain_db
            self._note(result, f"peak: measured {measured_peak_db:g} dB, target {s['peakTargetDb']:g} dB, "
                               f"gain {gain_db:+.2f} dB, onlyBoost={'on' if s['peakOnlyBoost'] else 'off'}")
            filters.append(f"volume={gain_db:.2f}dB")

        # loudnorm works internally at 192 kHz and, left alone, writes its
        # output at that rate; pin the output to the source's sample rate so
        # a 48 kHz recording stays 48 kHz (and the file stays the same size).
        rate_args: List[str] = []
        sample_rate = int(input_fmt.get("sampleRate", 0)) if input_fmt else 0
        if sample_rate > 0:
            rate_args = ["-ar", str(sample_rate)]

        # "-f wav" so the container never depends on the output extension.
        # Paths go in an argv list (no shell): no escaping needed.
        rc, _, err = self._run(
            [self.ffmpeg] + verbosity + seek_args + ["-y", "-i", src] + thread_args +
            ["-af", ",".join(filters) if filters else "anull", "-acodec", codec] + rate_args +
            ["-map_metadata", "-1", "-f", "wav", dst]
        )
        if rc != 0:
            raise NormalizeError(f"FFmpeg failed (exit code {rc}): {ffmpeg_error_tail(err)}")
        if not os.path.isfile(dst) or os.path.getsize(dst) <= 44:
            raise NormalizeError("FFmpeg wrote no audio")
        if self._cancel.is_set():
            raise NormalizeCanceled()
        ensure_plain_pcm_header(dst)
        self._note(result, f"written: {codec}")


__all__ = [
    "DEFAULT_SETTINGS", "NORM_MODES", "BIT_DEPTHS",
    "normalize_settings", "describe_settings",
    "NormalizeError", "NormalizeCanceled", "NormalizeResult", "Normalizer",
    "find_ff_tools", "probe_tool", "get_wav_format_info", "wav_header_duration",
    "choose_output_codec", "parse_loudnorm_json", "ffmpeg_error_tail",
    "ensure_plain_pcm_header",
]
