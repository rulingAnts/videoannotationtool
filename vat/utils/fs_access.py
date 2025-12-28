import os
import logging
from typing import List, Optional, Dict
from PySide6.QtCore import QObject, Signal


class FolderAccessError(Exception):
    pass


class FolderPermissionError(FolderAccessError):
    pass


class FolderNotFoundError(FolderAccessError):
    pass


class FolderAccessManager(QObject):
    """Centralized folder access checks and helpers to keep UI in sync.

    Emits optional signals to help the UI auto-refresh:
    - folderChanged(str): emitted with the new folder path (or empty string when cleared)
    - videosUpdated(list): emitted with the latest list of video file paths
    - metadataChanged(str): emitted with the latest metadata text after writes
    """

    folderChanged = Signal(str)
    videosUpdated = Signal(list)
    metadataChanged = Signal(str)
    imagesUpdated = Signal(str, list)

    VIDEO_EXTS = (".mpg", ".mpeg", ".mp4", ".avi", ".mkv", ".mov")

    def __init__(self):
        super().__init__()
        self.current_folder: Optional[str] = None
        self._videos_cache: List[str] = []
        self._images_cache: List[str] = []

    @staticmethod
    def is_accessible(path: str) -> bool:
        try:
            if not (path and os.path.isdir(path)):
                return False
            if not os.access(path, os.R_OK | os.X_OK):
                return False
            _ = os.listdir(path)
            return True
        except PermissionError:
            return False
        except Exception:
            return False

    def set_folder(self, path: str) -> bool:
        if path and os.path.isdir(path) and self.is_accessible(path):
            try:
                logging.info(f"FS.set_folder: path={path}")
            except Exception:
                pass
            self.current_folder = path
            try:
                self.folderChanged.emit(path)
            except Exception:
                pass
            self._refresh_videos()
            self._refresh_images()
            return True
        return False

    def clear_folder(self) -> None:
        self.current_folder = None
        try:
            self.folderChanged.emit("")
        except Exception:
            pass
        self._videos_cache = []

    def list_videos(self, path: Optional[str] = None) -> List[str]:
        folder = path or self.current_folder
        if not folder:
            return []
        if not os.path.isdir(folder):
            raise FolderNotFoundError(folder)
        if not self.is_accessible(folder):
            raise FolderPermissionError(folder)
        try:
            files = []
            for name in os.listdir(folder):
                full = os.path.join(folder, name)
                if os.path.isfile(full) and name.lower().endswith(self.VIDEO_EXTS):
                    files.append(full)
            files.sort()
            return files
        except PermissionError:
            raise FolderPermissionError(folder)
        except FileNotFoundError:
            raise FolderNotFoundError(folder)
        except Exception as e:
            raise FolderAccessError(str(e))

    def _refresh_videos(self) -> None:
        try:
            self._videos_cache = self.list_videos(self.current_folder)
            try:
                self.videosUpdated.emit(list(self._videos_cache))
            except Exception:
                pass
        except FolderAccessError:
            self._videos_cache = []

    def _refresh_images(self) -> None:
        try:
            self._images_cache = self.list_images(self.current_folder)
            try:
                logging.info(f"FS._refresh_images: count={len(self._images_cache)}")
            except Exception:
                pass
            try:
                self.imagesUpdated.emit(self.current_folder or "", list(self._images_cache))
            except Exception:
                pass
        except FolderAccessError:
            self._images_cache = []

    def ensure_and_read_metadata(self, folder: str, default_text: str) -> str:
        if not os.path.isdir(folder):
            raise FolderNotFoundError(folder)
        if not self.is_accessible(folder):
            raise FolderPermissionError(folder)
        path = os.path.join(folder, "metadata.txt")
        try:
            if not os.path.exists(path):
                with open(path, "w") as f:
                    f.write(default_text)
            with open(path, "r") as f:
                return f.read()
        except PermissionError:
            raise FolderPermissionError(folder)
        except Exception as e:
            raise FolderAccessError(str(e))

    def write_metadata(self, text: str) -> None:
        folder = self.current_folder
        if not folder:
            raise FolderAccessError("No current folder set")
        if not os.path.isdir(folder):
            raise FolderNotFoundError(folder)
        if not self.is_accessible(folder):
            raise FolderPermissionError(folder)
        path = os.path.join(folder, "metadata.txt")
        try:
            with open(path, "w") as f:
                f.write(text)
            try:
                self.metadataChanged.emit(text)
            except Exception:
                pass
        except PermissionError:
            raise FolderPermissionError(folder)
        except Exception as e:
            raise FolderAccessError(str(e))

    @staticmethod
    def video_basename(video_path: str) -> str:
        return os.path.splitext(os.path.basename(video_path))[0]

    def wav_path_for(self, video_or_name: str) -> str:
        folder = self.current_folder or os.path.dirname(video_or_name) or ""
        basename = os.path.splitext(os.path.basename(video_or_name))[0]
        return os.path.join(folder, basename + ".wav")

    def wav_path_for_image(self, image_or_name: str) -> str:
        # Prefer the image's own directory when a full path is provided;
        # otherwise fall back to the current folder.
        img_dir = os.path.dirname(image_or_name)
        folder = img_dir if img_dir else (self.current_folder or "")
        filename = os.path.basename(image_or_name)
        return os.path.join(folder, filename + ".wav")

    def has_image_audio(self, image_or_name: str) -> bool:
        return os.path.exists(self.wav_path_for_image(image_or_name))

    def image_recordings_in(self, folder: Optional[str] = None) -> List[str]:
        fold = folder or self.current_folder
        if not fold:
            return []
        try:
            images = self.list_images(fold)
            files = []
            for img in images:
                wp = self.wav_path_for_image(img)
                if os.path.exists(wp):
                    files.append(wp)
            files.sort()
            return files
        except FolderAccessError:
            return []

    def video_recordings_in(self, folder: Optional[str] = None) -> List[str]:
        fold = folder or self.current_folder
        if not fold:
            return []
        try:
            videos = self.list_videos(fold)
            files = []
            for vp in videos:
                name = os.path.basename(vp)
                wp = self.wav_path_for(name)
                if os.path.exists(wp):
                    files.append(wp)
            files.sort()
            return files
        except FolderAccessError:
            return []

    def recordings_in(self, folder: Optional[str] = None) -> List[str]:
        fold = folder or self.current_folder
        if not fold:
            return []
        if not os.path.isdir(fold):
            raise FolderNotFoundError(fold)
        if not self.is_accessible(fold):
            raise FolderPermissionError(fold)
        try:
            files = [os.path.join(fold, f) for f in os.listdir(fold) if f.lower().endswith('.wav') and not f.startswith('.')]
            files.sort()
            return files
        except PermissionError:
            raise FolderPermissionError(fold)
        except FileNotFoundError:
            raise FolderNotFoundError(fold)
        except Exception as e:
            raise FolderAccessError(str(e))

    def cleanup_hidden_files(self, folder: Optional[str] = None) -> List[str]:
        """Delete common hidden/junk files in the given folder.

        Behavior:
        - Always delete Windows hidden files by name (e.g., Thumbs.db, desktop.ini),
          regardless of platform. This helps when organizing Windows-originated folders
          on macOS/Linux.
        - Additionally, on Windows only, delete dot-prefixed files.

        Returns a list of error messages for files that could not be deleted.
        """
        errors: List[str] = []
        try:
            import sys as _sys
            fold = folder or self.current_folder
            if not fold:
                return errors
            # Safety checks
            if not os.path.isdir(fold):
                raise FolderNotFoundError(fold)
            if not self.is_accessible(fold):
                raise FolderPermissionError(fold)
            windows_hidden_names = {"Thumbs.db", "desktop.ini"}
            for f in os.listdir(fold):
                should_delete = False
                if f in windows_hidden_names:
                    should_delete = True
                elif _sys.platform == "win32" and f.startswith('.'):
                    should_delete = True
                if should_delete:
                    try:
                        os.remove(os.path.join(fold, f))
                    except Exception as e:
                        errors.append(f"Delete {f}: {e}")
        except FolderAccessError as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(str(e))
        return errors

    # Include common image extensions, notably both TIFF variants
    IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif")

    def list_images(self, path: Optional[str] = None) -> List[str]:
        folder = path or self.current_folder
        try:
            logging.debug(f"FS.list_images: folder={folder}")
        except Exception:
            pass
        if not folder:
            return []
        if not os.path.isdir(folder):
            raise FolderNotFoundError(folder)
        if not self.is_accessible(folder):
            raise FolderPermissionError(folder)
        try:
            files = []
            # Top-level images
            for name in os.listdir(folder):
                full = os.path.join(folder, name)
                if os.path.isfile(full) and name.lower().endswith(self.IMAGE_EXTS):
                    files.append(full)
            # Common subfolders that may contain images (non-recursive)
            for sub in ("images", "Images"):
                subpath = os.path.join(folder, sub)
                if os.path.isdir(subpath) and self.is_accessible(subpath):
                    for name in os.listdir(subpath):
                        full = os.path.join(subpath, name)
                        if os.path.isfile(full) and name.lower().endswith(self.IMAGE_EXTS):
                            files.append(full)
            files.sort()
            try:
                logging.info(f"FS.list_images: found={len(files)}; sample={[os.path.basename(f) for f in files[:3]]}")
            except Exception:
                pass
            return files
        except PermissionError:
            raise FolderPermissionError(folder)
        except FileNotFoundError:
            raise FolderNotFoundError(folder)
        except Exception as e:
            raise FolderAccessError(str(e))

    @staticmethod
    def image_basename(image_path: str) -> str:
        return os.path.splitext(os.path.basename(image_path))[0]

    @staticmethod
    def diagnose_access(path: str) -> Dict[str, bool]:
        info = {
            "exists": False,
            "isdir": False,
            "can_read": False,
            "can_exec": False,
            "listable": False,
        }
        try:
            info["exists"] = os.path.exists(path)
            info["isdir"] = os.path.isdir(path)
            info["can_read"] = os.access(path, os.R_OK)
            info["can_exec"] = os.access(path, os.X_OK)
            if info["isdir"] and info["can_read"] and info["can_exec"]:
                try:
                    _ = os.listdir(path)
                    info["listable"] = True
                except Exception:
                    info["listable"] = False
        except Exception:
            pass
        return info
