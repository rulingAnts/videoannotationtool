## Summary
Plan a mobile capture app to streamline media collection: take photos/videos, record audio descriptions for each, and offer a simple random review playback. Platforms: Android (native) and iPhone via Safari/WebKit fullscreen with offline capability. This is a subset of desktop features, focused on capture and simple review. Targets main branch.

## Background
Field collection benefits from immediate capture and annotation. A lightweight mobile workflow improves velocity and reduces friction, feeding the desktop app for deeper review and export.

## Goals
- Capture photos/videos and immediately record audio descriptions.
- Associate recordings with media using consistent naming.
- Simple random review playback with quick confirm (no grading/timers).
- Offline-first storage; export/sync to desktop (zip or folder).

## Non-Goals
- Advanced desktop features (grading, grouped export, Ocenaudio integration).

## User Stories
- As a user, I can capture an image/video and record its description in one flow.
- As a user, I can run a quick random playback to self-check on the phone.
- As a user, I can export/sync the captured set to the desktop app.

## Scope of Work
- Android native app: camera, audio recording, local storage, export.
- iPhone Safari/WebKit: PWA-like experience with fullscreen UI, service worker for offline storage, media capture via `<input capture>` and WebRTC where feasible.
- File naming compatibility with desktop: image.wav or basename.wav conventions.

## UI/UX Spec
- Capture flow: media → immediate audio record → save; list view of items with status.
- Review flow: random play prompt → select thumbnail → simple correct/incorrect feedback.
- Export: share zip/folder; QR or local network optional.

## Architecture & Files
- Separate repos/apps (mobile); desktop repo may include specs and sample data mapping.
- Define file/folder structure compatible with desktop `fs_access`.

## Settings & I18n Keys
- Minimal settings: language, storage location, export format.

## Events
- Capture start/stop, recording start/stop, export, review selection.

## Data & Persistence
- Local storage: files on device (Android: MediaStore/app storage; iOS: IndexedDB/Cache for web app).

## Integration Points
- Export zip/folder that the desktop app can ingest; include metadata.txt if useful.

## Error Handling & Resilience
- Handle camera/mic permissions gracefully; retry flows; offline availability.

## Performance
- Efficient media handling; background thread for encoding; responsive UI.

## Testing Plan
- Platform-specific unit tests; manual smoke tests; compatibility tests with desktop.

## Acceptance Criteria
- Capture + record works on both platforms; random review plays; export produces compatible structure; offline works on iPhone Safari.

## Telemetry / YAML Export
- Optional session YAML export for desktop ingestion.

## Localization
- UI localized; YAML remains English.

## Security & Privacy
- Respect platform permissions; local-only storage by default.

## Rollout Plan
- Phased: Android first, then iPhone web app.

## Open Questions
- Best sync mechanism (USB, AirDrop, QR/local network) and constraints.

## Coding Agent Notes
- Focus on capture + simple review; ensure export compatibility; keep UI minimal and robust.