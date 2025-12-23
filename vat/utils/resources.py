import os
import sys
import shutil
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
        return os.path.join(base_dir, relative_path)
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


def configure_pydub_ffmpeg():
    ffmpeg_path = resource_path(os.path.join("ffmpeg", "bin", "ffmpeg"))
    ffprobe_path = resource_path(os.path.join("ffmpeg", "bin", "ffprobe"))
    ffmpeg_dir = os.path.dirname(ffmpeg_path)
    if os.path.exists(ffmpeg_dir):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    if os.path.exists(ffmpeg_path):
        os.environ["PYDUB_FFMPEG"] = ffmpeg_path
    if os.path.exists(ffprobe_path):
        os.environ["PYDUB_FFPROBE"] = ffprobe_path
