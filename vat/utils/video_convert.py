import os
import re
import shutil
import subprocess
from dataclasses import dataclass
import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal, QThread

from vat.utils.resources import resolve_ff_tools


def _probe_duration(ffprobe_path: str, src_path: str) -> Optional[float]:
    try:
        cmd = [
            ffprobe_path,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=nokey=1:noprint_wrappers=1",
            src_path,
        ]
        out = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if out.returncode != 0:
            return None
        s = out.stdout.decode().strip()
        return float(s) if s else None
    except Exception:
        return None


def _probe_stream_info(ffprobe_path: str, src_path: str):
    info = {
        "v_codec": None,
        "v_pix_fmt": None,
        "has_audio": False,
        "a_codec": None,
    }
    try:
        # Video codec + pixel format
        cmd_v = [
            ffprobe_path,
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,pix_fmt",
            "-of", "default=nokey=1:noprint_wrappers=1",
            src_path,
        ]
        out_v = subprocess.run(cmd_v, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if out_v.returncode == 0:
            lines = [l.strip() for l in out_v.stdout.decode().splitlines() if l.strip()]
            if lines:
                info["v_codec"] = lines[0] if len(lines) >= 1 else None
                info["v_pix_fmt"] = lines[1] if len(lines) >= 2 else None
        # Audio codec (if present)
        cmd_a = [
            ffprobe_path,
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_name",
            "-of", "default=nokey=1:noprint_wrappers=1",
            src_path,
        ]
        out_a = subprocess.run(cmd_a, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if out_a.returncode == 0:
            a_lines = [l.strip() for l in out_a.stdout.decode().splitlines() if l.strip()]
            if a_lines:
                info["has_audio"] = True
                info["a_codec"] = a_lines[0]
    except Exception:
        pass
    return info


def needs_reencode_to_mp4(src_path: str) -> bool:
    tools = resolve_ff_tools()
    ffprobe = tools["ffprobe"]
    if not ffprobe:
        return True
    # If not .mp4, we will re-encode
    if os.path.splitext(src_path)[1].lower() != ".mp4":
        return True
    inf = _probe_stream_info(ffprobe, src_path)
    # Require H.264 video with yuv420p for compatibility
    if (inf.get("v_codec") or "").lower() != "h264":
        return True
    if (inf.get("v_pix_fmt") or "").lower() != "yuv420p":
        return True
    # If audio present, require AAC
    if inf.get("has_audio") and (inf.get("a_codec") or "").lower() != "aac":
        return True
    return False


@dataclass
class ConvertSpec:
    src_path: str
    dst_path: str


class VideoConvertWorker(QThread):
    progress = Signal(int)            # 0..100
    finished = Signal(str)            # dst_path
    error = Signal(str)               # message
    canceled = Signal()               # canceled

    def __init__(self, spec: ConvertSpec):
        super().__init__()
        self.spec = spec
        self._cancel = False
        self._proc: Optional[subprocess.Popen] = None
        tools = resolve_ff_tools()
        self.ffmpeg = tools["ffmpeg"]
        self.ffprobe = tools["ffprobe"]
        # Execution state for fallback handling
        self.succeeded: bool = False
        self.had_error: bool = False
        self.was_canceled: bool = False
        self.output_path: Optional[str] = None

    def cancel(self):
        self._cancel = True
        try:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
        except Exception:
            pass

    def run(self):
        try:
            src = self.spec.src_path
            dst = self.spec.dst_path
            if not (src and os.path.exists(src)):
                self.error.emit("Source file missing")
                return
            if not self.ffmpeg:
                self.error.emit("FFmpeg not found")
                return
            # Probe duration and audio presence for better progress + args
            duration = _probe_duration(self.ffprobe, src) if self.ffprobe else None
            streams = _probe_stream_info(self.ffprobe, src) if self.ffprobe else {"has_audio": False}
            audio_args = ["-an"] if not streams.get("has_audio") else ["-c:a", "aac", "-b:a", "128k"]
            try:
                logging.info(f"FF.worker: start: src={src}, dst={dst}, duration={duration}, has_audio={streams.get('has_audio')}, ffmpeg={self.ffmpeg}")
            except Exception:
                pass
            cmd = [
                self.ffmpeg, "-y", "-i", src,
                "-c:v", "libx264", "-preset", "fast", "-movflags", "+faststart", "-pix_fmt", "yuv420p",
                *audio_args,
                dst,
            ]
            self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.?\d*)")
            # Parse stderr for progress
            while True:
                if self._cancel:
                    try:
                        if self._proc and self._proc.poll() is None:
                            self._proc.terminate()
                    except Exception:
                        pass
                    self.was_canceled = True
                    self.canceled.emit()
                    try:
                        logging.info("FF.worker: canceled")
                    except Exception:
                        pass
                    return
                line = self._proc.stderr.readline()
                if not line:
                    if self._proc.poll() is not None:
                        break
                    continue
                m = time_pattern.search(line)
                if m and duration and duration > 0:
                    h, m_, s = m.groups()
                    cur = int(h) * 3600 + int(m_) * 60 + float(s)
                    pct = int(max(0.0, min(100.0, (cur / duration) * 100)))
                    self.progress.emit(pct)
            rc = self._proc.wait()
            if rc != 0:
                err = self._proc.stderr.read() if self._proc.stderr else ""
                try:
                    logging.error(f"FF.worker: rc={rc}, err={err[:400] if isinstance(err, str) else err}")
                except Exception:
                    pass
                self.had_error = True
                self.error.emit(err or "Conversion failed")
                return
            if not os.path.exists(dst):
                self.had_error = True
                self.error.emit("Output missing after conversion")
                return
            self.progress.emit(100)
            try:
                logging.info(f"FF.worker: finished ok: out={dst}")
            except Exception:
                pass
            self.succeeded = True
            self.output_path = dst
            self.finished.emit(dst)
        except Exception as e:
            try:
                logging.error(f"FF.worker: exception: {e}")
            except Exception:
                pass
            self.had_error = True
            self.error.emit(str(e))
