# Visual Stimulus Kit Tool v2.1.0 — Release Draft

## Overview
This release introduces the Review experience and streamlines remote workflows for WhatsApp. You can now quiz participants, grade fairly, export grouped/YAML results, and quickly import media with built-in conversions that ensure broad device compatibility.

## Highlights
- Review tab: quiz-based review with fairness, timing, grading, and export
- WhatsApp-friendly media imports: MOV/MPG/AVI → MP4; HEIC/HEIF → JPG
- Robust conversions with progress UI and background workers
- Clipboard audio workflows: paste audio for videos/images and auto-convert to WAV
- Stability hardening: thread lifecycle fixes, atomic file writes, long-video warnings

## Changes
- New: Review feature
  - [vat/review/review_tab.py](vat/review/review_tab.py)
  - [vat/review/thumbnail_grid.py](vat/review/thumbnail_grid.py)
  - [vat/review/session_state.py](vat/review/session_state.py)
  - [vat/review/stats.py](vat/review/stats.py)
  - [vat/review/queue.py](vat/review/queue.py)
  - [vat/review/yaml_exporter.py](vat/review/yaml_exporter.py)
  - [vat/review/grouped_export_dialog.py](vat/review/grouped_export_dialog.py)
  - [vat/review/grouped_exporter.py](vat/review/grouped_exporter.py)
- Media import and conversion
  - Images tab: Add image… + default Convert to JPG
  - Videos tab: Add video… + default Convert to MP4
  - HEIC/HEIF support via Pillow+pillow-heif with orientation handling
  - [vat/utils/image_convert.py](vat/utils/image_convert.py) — background worker with atomic writes
  - [vat/utils/video_convert.py](vat/utils/video_convert.py) — MP4 conversion worker with progress
  - [vat/ui/app.py](vat/ui/app.py) — dialogs, progress, lifecycle management, EXIF-aware loading
  - [vat/utils/fs_access.py](vat/utils/fs_access.py) — broadened image listings (.heic/.heif/.webp)
- Clipboard audio workflows
  - Paste audio for videos and images with 16-bit WAV conversion
  - Persistent audio thread; playback and stop consistency
- Stability and UX
  - Atomic JPG writes; validation before UI refresh
  - Long video conversion warning with non-blocking progress
  - Suppress unrelated video retry prompts during image imports
  - EXIF-aware image orientation for thumbnails and fullscreen

## Notable Files
- Core UI: [vat/ui/app.py](vat/ui/app.py)
- Review system: see files under [vat/review/](vat/review)
- Converters: [vat/utils/image_convert.py](vat/utils/image_convert.py), [vat/utils/video_convert.py](vat/utils/video_convert.py)
- FS: [vat/utils/fs_access.py](vat/utils/fs_access.py)

## Upgrade Notes
- Requirements updated: Pillow HEIC support (`pillow-heif`) added
- FFmpeg/FFprobe are detected system-wide; ensure they’re installed

## Known Limitations
- Image cancel stops UI spinner immediately; conversion may finish in background
- Extremely long video conversions may take time but remain stable

## Credits
Thanks to the research workflow improvements and review capabilities driven in this release.
