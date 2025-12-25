import os
from typing import List


class FolderAccessError(Exception):
    pass


class FolderPermissionError(FolderAccessError):
    pass


class FolderNotFoundError(FolderAccessError):
    pass


class FolderAccessManager:
    """Centralized folder access checks and helpers to keep UI in sync."""

    VIDEO_EXTS = (".mpg", ".mpeg", ".mp4", ".avi", ".mkv", ".mov")

    def __init__(self):
        self.current_folder: str | None = None

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
            self.current_folder = path
            return True
        return False

    def list_videos(self, path: str | None = None) -> List[str]:
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
