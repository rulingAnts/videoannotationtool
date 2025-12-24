import os
import sys
import shutil
import logging
import cv2

# Helper for PyInstaller runtime resource resolution

def resource_path(relative_path, check_system=True):
    """Get absolute path to resource, works for dev and PyInstaller (onefile/onedir)."""
    if check_system:
        binary_name = os.path.basename(relative_path)
        system_path = shutil.which(binary_name)
        if system_path:
            return system_path
    if hasattr(sys, '_MEIPASS') and sys._MEIPASS:
        return os.path.join(sys._MEIPASS, relative_path)
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
        # macOS app bundle structure may place resources under Contents/Resources or Contents/Frameworks
        # Try MacOS, then Resources, then Frameworks.
        candidates = [
            os.path.join(base_dir, relative_path),
            os.path.join(os.path.dirname(base_dir), 'Resources', relative_path),
            os.path.join(os.path.dirname(base_dir), 'Frameworks', relative_path),
        ]
        for cand in candidates:
            if os.path.exists(cand):
                return cand
        # Fall back to MacOS-relative path
        return candidates[0]
    return os.path.join(os.path.abspath("."), relative_path)


def configure_opencv_ffmpeg():
    dll_name = "opencv_videoio_ffmpeg4120_64.dll"
    opencv_dir = os.path.dirname(cv2.__file__)
    system_dll_path = os.path.join(opencv_dir, dll_name)
    if os.path.exists(system_dll_path):
        os.environ["OPENCV_FFMPEG_DLL_DIR"] = opencv_dir
        os.environ["PATH"] = opencv_dir + os.pathsep + os.environ.get("PATH", "")
    else:
        bundled_dll_path = resource_path(dll_name, check_system=False)
        if os.path.exists(bundled_dll_path):
            os.environ["OPENCV_FFMPEG_DLL_DIR"] = os.path.dirname(bundled_dll_path)
            os.environ["PATH"] = os.path.dirname(bundled_dll_path) + os.pathsep + os.environ.get("PATH", "")


def resolve_ff_tools():
    """Resolve ffmpeg/ffprobe paths and origin (bundled/system). Returns dict."""
    # Prefer bundled ffmpeg under ffmpeg/bin across Mac/Linux/Windows
    base_rel = os.path.join("ffmpeg", "bin")
    ffmpeg_path = resource_path(os.path.join(base_rel, "ffmpeg"), check_system=False)
    ffprobe_path = resource_path(os.path.join(base_rel, "ffprobe"), check_system=False)
    # On Windows, the bundled files may have .exe suffix
    ffmpeg_exe = ffmpeg_path + ".exe"
    ffprobe_exe = ffprobe_path + ".exe"
    chosen_ffmpeg = None
    chosen_ffprobe = None
    if os.path.exists(ffmpeg_path):
        chosen_ffmpeg = ffmpeg_path
    elif os.path.exists(ffmpeg_exe):
        chosen_ffmpeg = ffmpeg_exe
    if os.path.exists(ffprobe_path):
        chosen_ffprobe = ffprobe_path
    elif os.path.exists(ffprobe_exe):
        chosen_ffprobe = ffprobe_exe
    # If bundled not found, fall back to system PATH
    if not chosen_ffmpeg:
        sys_ffmpeg = shutil.which("ffmpeg")
        if sys_ffmpeg:
            chosen_ffmpeg = sys_ffmpeg
    if not chosen_ffprobe:
        sys_ffprobe = shutil.which("ffprobe")
        if sys_ffprobe:
            chosen_ffprobe = sys_ffprobe
    src_ffmpeg = "bundled" if chosen_ffmpeg and (chosen_ffmpeg == ffmpeg_path or chosen_ffmpeg == ffmpeg_exe) else ("system" if chosen_ffmpeg else "none")
    src_ffprobe = "bundled" if chosen_ffprobe and (chosen_ffprobe == ffprobe_path or chosen_ffprobe == ffprobe_exe) else ("system" if chosen_ffprobe else "none")
    return {
        "ffmpeg": chosen_ffmpeg,
        "ffprobe": chosen_ffprobe,
        "ffmpeg_origin": src_ffmpeg,
        "ffprobe_origin": src_ffprobe,
        "ffmpeg_bin_dir": os.path.dirname(chosen_ffmpeg) if chosen_ffmpeg else None,
        "ffprobe_bin_dir": os.path.dirname(chosen_ffprobe) if chosen_ffprobe else None,
    }


def configure_pydub_ffmpeg():
    info = resolve_ff_tools()
    chosen_ffmpeg = info["ffmpeg"]
    chosen_ffprobe = info["ffprobe"]
    ffmpeg_dir = info["ffmpeg_bin_dir"]
    # Update PATH and pydub env vars if we have anything
    if chosen_ffmpeg:
        os.environ["PYDUB_FFMPEG"] = chosen_ffmpeg
        if ffmpeg_dir and os.path.exists(ffmpeg_dir):
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    if chosen_ffprobe:
        os.environ["PYDUB_FFPROBE"] = chosen_ffprobe
    # Log the resolved tools for verification (visible in --debug runs)
    try:
        logging.info(f"FFmpeg resolved: {chosen_ffmpeg or 'none'} ({info['ffmpeg_origin']})")
        logging.info(f"FFprobe resolved: {chosen_ffprobe or 'none'} ({info['ffprobe_origin']})")
    except Exception:
        pass
