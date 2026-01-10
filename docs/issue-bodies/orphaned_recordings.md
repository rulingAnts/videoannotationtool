## Summary
Add a new tab that lists audio recordings (WAV) that don’t have a corresponding image or video, and provides ways to attach/import media (image or video) or capture via webcam, then pair the media to the recording. Targets main branch.

## Background
Users sometimes record descriptions before capturing media, or files get moved/renamed. This tab simplifies pairing orphaned WAVs with visuals, maintaining consistent naming conventions and enabling downstream review activities.

## Goals
- Detect and list orphaned recordings (WAVs without matching image or video).
- Preview/play WAV; quick inspect metadata.
- Attach existing media via import (image/video), or capture via webcam.
- Pair/rename/move files to match conventions (image: filename.wav; video: basename.wav).
- Validate and show success/failure non-blockingly; localized UI.
- Optional YAML report of pairing actions for audit.

## Non-Goals
- Audio editing or noise reduction.
- Complex metadata editing beyond pairing and file moves.

## User Stories
- As a user, I can see recordings without matching media and fix them quickly.
- As a user, I can capture an image/video via webcam and pair it to an orphaned WAV.

## Scope of Work
- Filesystem scan: use `fs_access` to list WAVs and media, compute orphans.
- UI: new tab with searchable/sortable list; columns: filename, duration, suggested match, status.
- Actions: Play, Import Image, Import Video, Webcam Capture, Pair, Move (with overwrite prompts), Undo (last action).

## UI/UX Spec
- Header: filters, search, buttons for import/capture.
- List: per-row actions; status badges; non-blocking messages.
- Webcam: cross-platform approach (Qt Multimedia if available; fallback OpenCV).
- Localization: strings in existing i18n system.

## Architecture & Files
- `vat/ui/app.py`: new tab UI and wiring.
- `vat/utils/fs_access.py`: orphan detection helpers.
- `vat/ui/webcam.py` (new): capture image/video.
- `vat/utils/pairing.py` (new): rename/move + validations.

## Settings & I18n Keys
- `orphaned.lastImportFolder`, `orphaned.webcam.defaults`, localized labels/buttons/messages.

## Signals & Slots / Events
- Signals: `orphanListReady`, `pairingCompleted`, `captureReady`.
- Events: file chooser, webcam start/stop, pairing commit.

## Data & Persistence
- File operations: copy/move/rename; update naming conventions; optional YAML audit log.

## Integration Points
- Consistent naming so recordings appear in Images/Videos/Review tabs.

## Error Handling & Resilience
- Non-blocking notifications for minor issues; dialogs for critical actions.

## Performance
- Lazy loading for list; lightweight audio preview.

## Testing Plan
- Unit: orphan detection, pairing rules, rename/move validations.
- UI smoke: import, capture, pair flows.

## Acceptance Criteria
- Orphans listed accurately, pairing works (import & webcam), files renamed/moved correctly, localized, non-blocking messages.

## Telemetry / YAML Export
- Optional YAML: actions taken, old/new paths, timestamps, success/fail.

## Localization
- All UI strings localized; YAML remains English.

## Security & Privacy
- Webcam prompts and permissions; local-only storage.

## Rollout Plan
- Feature enabled by default; docs updated.

## Open Questions
- Preferred webcam stack across platforms if Qt Multimedia isn’t available.

## Coding Agent Notes
- Follow repo style; add minimal new modules; use existing helpers; ensure cross-platform webcam or provide import-only fallback.