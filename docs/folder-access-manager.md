# Folder Access Manager: Design and Multi‑Tab Sync

This document describes how `FolderAccessManager` centralizes folder state and filesystem access so all tabs and UI panels stay synchronized, predictable, and resilient.

## Goals
- Single source of truth for the selected folder
- Consistent, permission‑safe filesystem access
- Predictable errors mapped to clear UI messages
- Easy synchronization across tabs via shared state and optional signals

## Current Capabilities
- **State:** `current_folder: str | None` tracks the active folder
- **Validation:** `set_folder(path) -> bool` uses `is_accessible()` to ensure existence + permissions
- **Access check:** `is_accessible(path) -> bool` verifies directory, `R_OK|X_OK`, and lists contents safely
- **Video listing:** `list_videos(path?: str) -> List[str]` returns sorted full paths for standard video extensions
- **Metadata:** `ensure_and_read_metadata(folder, default_text) -> str` creates `metadata.txt` if missing, then reads it
- **Exceptions:** Raises `FolderNotFoundError`, `FolderPermissionError`, `FolderAccessError` for clear UI handling

## Why It Keeps Tabs in Sync
- **Single source of truth:** All panels pull from `fs.current_folder` and call `fs.*` methods—no scattered `os.*` calls
- **Unified behavior:** Same extensions, sorting, and error mapping everywhere
- **Typed errors:** Straightforward, consistent UI responses (permission denied vs. not found vs. unexpected)

## Recommended Usage Pattern
- **Create one shared instance** at app startup:
  - In the main window: `self.fs = FolderAccessManager()`
  - Inject `self.fs` into each tab/panel constructor
- **Remove per‑tab folder variables:** Always read from `fs.current_folder`
- **Centralize I/O:**
  - Videos: `fs.list_videos()`
  - Metadata: `fs.ensure_and_read_metadata()` and a future `fs.write_metadata(text)`
  - Derivatives: add helpers (see Evolution) to avoid duplicating path logic
- **Map errors consistently:**
  - `FolderPermissionError` → warning prompt + disable actions
  - `FolderNotFoundError` → info prompt + clear state
  - `FolderAccessError` → error prompt + diagnostics option

## Evented Sync (Optional, Recommended)
Upgrade `FolderAccessManager` to emit signals so UI updates automatically.

- Make it a `QObject` with signals:
  - `folderChanged: Signal(str)` — emitted after `set_folder()` succeeds
  - `videosUpdated: Signal(list[str])` — emitted after scans/refreshes
  - `metadataChanged: Signal(str)` — emitted after writes
- Panels connect once and refresh themselves when signals fire—no manual reload calls sprinkled around.

### Sketch
```python
class FolderAccessManager(QObject):
    folderChanged = Signal(str)
    videosUpdated = Signal(list)
    metadataChanged = Signal(str)

    def set_folder(self, path: str) -> bool:
        if self.is_accessible(path):
            self.current_folder = path
            self.folderChanged.emit(path)
            self._refresh_videos()
            return True
        return False

    def _refresh_videos(self):
        self._videos_cache = self.list_videos(self.current_folder)
        self.videosUpdated.emit(self._videos_cache)

    def write_metadata(self, text: str):
        # write file, then
        self.metadataChanged.emit(text)
```

## Minimal API Evolution
Add small, focused helpers to keep UI logic clean:
- `clear_folder()` — resets `current_folder` and emits `folderChanged` with `""` or `None`
- `write_metadata(text: str) -> None`
- `wav_path_for(video_path: str) -> str` — resolves sibling WAV by basename
- `video_basename(video_path: str) -> str` — utility for UI labels
- `recordings_in(folder?: str) -> List[str]` — enumerates `.wav` files for the current folder
- `diagnose_access(path: str) -> dict` — returns details (exists, isdir, perms, listable) for better prompts

## Enhancements (Nice‑to‑Have)
- **Caching + invalidation:** cache video lists; invalidate on explicit refresh or via `QFileSystemWatcher`
- **Constants:** expose `VIDEO_EXTS` for reuse in UI components
- **Import/export helpers:** shared routines for batch operations (export/import paths and validations)
- **Permission diagnostics UI:** surface `diagnose_access()` in a help dialog for users

## Migration Guide (Step‑by‑Step)
1. Instantiate a single `FolderAccessManager` in the main window; pass to all tabs
2. Replace direct `os.*` calls with `fs.*` methods
3. Remove per‑tab `folder_path`; read `fs.current_folder` everywhere
4. Map exceptions to consistent UI prompts
5. (Optional) Convert `FolderAccessManager` to `QObject` and wire signals to auto‑refresh panels

## Build/Packaging Notes (Universal App)
- **PyAudio strict import:** Avoid requiring `pyaudio._portaudio` unless you guarantee the native extension is packaged; otherwise recording will be disabled
- **PyInstaller hidden imports:** Ensure PySide6 modules are discoverable when switching to universal binaries
- **`target_arch='universal2'`:** Reintroduce incrementally with runtime checks; validate both arch slices for bundled deps

## Testing Checklist
- Switching folders updates all panels immediately (or on signal)
- Permission‑restricted folders prompt and disable actions consistently
- Missing folders clear state without crashes
- Video listing identical across tabs (order, extensions)
- Metadata create/read/write consistent across tabs

## Future Centralization Reminder
Investigate any other parts of our app that should be centralized this way for consistency across the app, instead of individual UI elements, objects, and functions instantiating things that should be shared app‑wide. Capture candidates (e.g., audio device selection, ffmpeg path/diagnostics, metadata lifecycle, import/export flows) and move them into shared managers with clear APIs and, where useful, signals.
```
