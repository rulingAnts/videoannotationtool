Review Tab (Dirty Dozen) — Plan

Goals
- Recorded-only review: show only thumbnails (images/videos) that have matching recordings in the queue.
- Quick confirm: right-click, Ctrl/Cmd+Click, or Enter confirms; single-click selects; double-click previews/fullscreens.
- Fairness: randomized prompts that evenly distribute repeats and avoid clustering.
- Timing: per-item decision timer pauses during fullscreen video playback; subtract small UI overhead.
- Grading: adjustable time weighting; clear grade thresholds; session stats and “Trouble Items”.
- Scope-aware actions: Ocenaudio and single-WAV export respect the review tab’s filtered scope.
- Grouped export: split recorded items into folders based on user slider (items per folder or number of folders).
- Persistence & reset: all session settings persist and can be reset to defaults.
- Localization: all UI strings localized; YAML stats export remains English.
- Resilience & performance: non-blocking notifications, preloading, smooth UI.

Defaults
Defaults (Quick Reference)
| Setting | Default |
| --- | --- |
| Scope | Both (images + videos) |
| Play Count per Item | 1 |
| Time Weighting | 30% |
| Per-Item Time Limit | Off (Soft when enabled) |
| Limit Mode | Soft |
| UI Overhead Baseline | 600 ms |
| Sound Effects | On |
| SFX Volume | 70% |
| SFX Tone | Default |
| Grouped Export | 12 items per folder |
| Quick Confirm Mode | On |
- Scope: Both (images + videos)
- Play Count per Item: 1
- Time Weighting: 30% (slider 0–100%)
- Per-Item Time Limit: Off by default (soft limit when enabled)
- Limit Mode: Soft
- UI Overhead Baseline: 600 ms (toggle/slider)
- Sound Effects: On (ding for correct, buzzer for wrong)
- SFX Volume: 70% (slider)
- SFX Tone: Default (option: Gentle)
- Grouped Export: 12 items per folder (show remainder in last folder)

UI Layout (Review Tab Header)
- Controls row:
  - Scope: Images / Videos / Both
  - Play Count per Item (numeric)
  - Per-Item Time Limit (seconds, numeric)
  - Limit Mode: Soft / Hard
  - Sound Effects: On/Off, SFX Volume slider, Tone selector
  - Time Weighting slider (0–100%)
  - UI Overhead toggle/slider (baseline subtraction)
  - Start Review • Pause/Resume • Stop • Reset • Reset to Defaults
  - Export YAML Report • Grouped Export
- Tip (under header): “Single-click selects. Right-click, Ctrl/Cmd+Click, or Enter confirms. Double-click opens preview/fullscreen.”
- Progress & timing: progress bar, per-item countdown (visible when limit enabled).

Recorded-only Scope
- Populate grid from recorded sets using fs_access helpers:
  - Images: include only images with adjacent WAVs (full filename + .wav)
  - Videos: include only videos with matching-basename WAVs (basename + .wav)
- The randomized audio queue is built exclusively from these recorded items.

Quick Confirm & Controls
- Single-click: selects thumbnail (no confirm).
- Right-click or Ctrl/Cmd+Click: immediate confirm.
- Enter/Return: confirm selected item (via itemActivated).
- Double-click: preview/fullscreen (image zoom/pan, video play/pause); does not confirm.
- Feedback overlays: green border/check for correct; red border/X for wrong; overlays persist until correct or stop/reset.

Audio Queue & Randomization Fairness
- “Fairness” means distributing prompts uniformly across items:
  - Shuffle without replacement per round.
  - If Play Count > 1: implement multiple rounds, each round a fresh shuffle.
  - Optionally rotate order across rounds to avoid consistent positional bias.
- Avoid clusters: do not repeat the same item back-to-back unless items are scarce.

Timing & Grading
- Decision time:
  - Start when prompt plays; pause while fullscreen video is playing.
  - Subtract UI Overhead baseline (default 600 ms) from measured time.
- Time efficiency score: Ts = clamp((Tmax - (t̄ - t_baseline)) / (Tmax - Topt), 0, 1)
  - Topt = 2 s, Tmax = 10 s, t_baseline = user setting (default 0.6 s)
- Composite grade: S = (1 - w)·A + w·Ts
  - A = overall accuracy (percent correct)
  - w = time weighting slider in [0,1]
- Letter thresholds:
  - A+: S ≥ 0.95; A: S ≥ 0.90; B+: S ≥ 0.80; B: S ≥ 0.75
  - C+: S ≥ 0.70; C: S ≥ 0.65; D: S ≥ 0.55; F otherwise
- Timer modes:
  - Soft limit: on expiry, mark “overtime” and continue; primarily affects Ts.
  - Hard limit: on expiry, auto mark wrong (timeout) and optionally auto-replay once.

Stats & YAML Export
- Per-item: wrongGuesses, timeToCorrect, overtime flags, confirm path (mouse/keyboard), media type.
- Overall: accuracy, mean/median time, time weighting, UI overhead, limit mode, scope, play count, SFX settings, language, app version, timestamps.
- Trouble Items: sorted by longest time then most wrong guesses; include thumbnail ref and WAV path.
- Export: human-readable YAML (English only) via PyYAML; file name includes session timestamp.

Grouped Export
- UI: slider + radio choice:
  - Items per folder (default 12) OR Number of folders.
- Behavior:
  - Split the current filtered scope (images/videos/both with recordings) into group folders: Group 01, Group 02, …
  - Copy each item with its matching WAV into its group folder.
  - Show a summary indicating the remainder in the last folder.
  - Default is copy (safer); optional “Move” toggle with warning.

Session Lifecycle
- Start: build queue, enable feedback, disable mutable controls.
- Pause/Resume: freeze timers and playback; maintain current prompt state.
- Stop: end session; prompt to keep stats.
- Reset: clear feedback and stats; keep settings unless “Reset to Defaults”.
- Reset to Defaults: restore baseline defaults and persist.

Localization
- Add all new strings to existing i18n labels; ensure language switches update header, tips, controls, and notifications.
- YAML export remains English for interoperability.

Error Resilience & Performance
- Non-blocking notifications (status bar or inline header messages) for minor issues.
- Dialogs only for confirmations and critical errors.
- Preload visible thumbnails and small audio buffers; avoid UI stutter on scroll.

Ocenaudio / Single-WAV Export
- Respect the review tab’s filtered scope when launching Ocenaudio and joining single WAV exports.
- Use existing helpers and worker patterns; ensure consistent ffmpeg/ffprobe resolution.

Implementation Notes
- Encapsulate the thumbnail grid as a reusable widget (ThumbnailGridWidget) with selection and quick confirm handlers.
- Add a playing_changed signal to FullscreenVideoViewer to pause/resume the decision timer.
- Persist new settings (scope, play count, limits, SFX, time weighting, UI overhead) via existing JSON helpers.
- Keep YAML in English; localize all added UI strings; provide a “Reset to Defaults” button.

Randomization Fairness (Stakeholder Note)
- Goal: ensure each recorded item gets a balanced number of prompts without clustering, improving recall and reducing frustration.
- Method: per-round shuffle without replacement; if Play Count > 1, create multiple rounds and rotate order across rounds to avoid positional bias; never serve the same item twice in a row unless item count is too small.
- Optional: allow a debug seed for reproducible sessions.

Implementation Scope
- Review tab with recorded-only grid, header controls, quick confirm, progress bar, per-item timer (soft/hard), sound effects, YAML stats export, grouped export, Ocenaudio/single-WAV scope-awareness, settings persistence, and Reset to Defaults.

Architecture & Components
- ReviewTab (UI): Header controls, tip, progress/timer, grid; wires events and orchestrates session.
- ThumbnailGridWidget: Encapsulates icon-mode grid, selection, double-click preview, quick confirm handlers; exposes signals.
- ReviewSessionState: Holds persisted settings (scope, play count, limit, weighting, overhead, SFX) and transient session state.
- ReviewQueue: Builds randomized audio queue from recorded items; enforces fairness rules; emits next prompt.
- ReviewStats: Tracks per-item stats, aggregates overall metrics, computes composite grade.
- YAMLExporter: Produces human-readable YAML report per plan specs.
- GroupedExporter: Splits filtered scope into folders by items-per-folder or number-of-folders; copies media + matching WAVs.

Signals & Slots
- ThumbnailGridWidget
  - signals: selectionChanged(itemId), activatedConfirm(itemId, method)
  - events: mousePress (right-click, Ctrl/Cmd+Click), itemActivated (Enter/Return), doubleClicked (preview)
- ReviewQueue
  - signals: promptReady(itemId, wavPath), queueFinished()
- ReviewTab
  - slots: onStart(), onPauseResume(), onStop(), onReset(), onResetDefaults()
  - slots: onConfirm(itemId), onPromptAdvance(), onTimeout()
  - signals: feedbackChanged(itemId, state), statsUpdated(overall)
- FullscreenVideoViewer
  - signals: playingChanged(isPlaying) for timer pause/resume

Settings Keys (JSON)
- review.scope: "Images" | "Videos" | "Both"
- review.playCountPerItem: int
- review.perItemTimeLimitSec: int or null
- review.limitMode: "Soft" | "Hard"
- review.timeWeightingPercent: 0–100
- review.uiOverheadMs: int
- review.sfx.enabled: bool
- review.sfx.volumePercent: 0–100
- review.sfx.tone: "Default" | "Gentle"
- review.quickConfirmMode: bool
- review.grouped.defaultItemsPerFolder: int (default 12)
- review.resetDefaultsLastUsed: timestamp (optional)

I18n Keys (Labels/Tips)
- review.scope.label, review.scope.images, review.scope.videos, review.scope.both
- review.playCount.label
- review.timeLimit.label, review.limitMode.soft, review.limitMode.hard
- review.sfx.enabled.label, review.sfx.volume.label, review.sfx.tone.label, review.sfx.tone.default, review.sfx.tone.gentle
- review.timeWeighting.label, review.uiOverhead.label
- review.controls.start, review.controls.pause, review.controls.resume, review.controls.stop, review.controls.reset, review.controls.resetDefaults
- review.export.yaml.label, review.export.grouped.label
- review.tip.quickConfirm
- review.progress.label, review.timer.label
- review.feedback.correct, review.feedback.wrong, review.feedback.timeout, review.feedback.overtime
- review.dialog.stop.keepStats
- review.notification.scopeEmpty, review.notification.missingWav, review.notification.exportDone, review.notification.exportError

Error Handling
- Non-blocking status messages for minor issues (e.g., missing WAV in scope); dialogs for confirmations (Stop/Reset) and critical failures (export write errors).
- Graceful skips on corrupt media/WAVs with a count summary at end.
- Validate destination paths for grouped export; preflight free space where feasible.

Performance
- Preload visible thumbnails and small audio buffers; lazy-load when scrolling.
- Avoid repaint thrash by batching feedback updates; use timers judiciously.
- Ensure audio playback runs in worker threads; UI only receives signals.

Testing Plan
- Unit: fs_access filtering (recorded-only), ReviewQueue fairness (no duplicates in a round, even distribution across repeats), YAMLExporter (schema + example), GroupedExporter (correct grouping and remainder), Stats aggregation (composite score, letter grade), timer pause/resume on playingChanged.
- UI smoke: selection, quick confirm (right-click, Ctrl/Cmd+Click, Enter), double-click preview, progress/timer behavior, soft vs hard limit.
- Integration: scope-aware Ocenaudio/single-WAV export sources from Review tab.
- Error paths: missing/invalid WAVs, export failures, invalid destination paths; verify non-blocking notifications.

Acceptance Criteria
- Recorded-only grid and queue; only items with WAVs are displayed and quizzed.
- Quick confirm works via right-click, Ctrl/Cmd+Click, Enter; double-click previews only.
- Timer pauses during fullscreen video playback; UI overhead subtraction applied; soft/hard modes behave per spec.
- Fairness: per-round shuffle without replacement; no immediate repeats; repeats distributed evenly when Play Count > 1.
- Stats and grade computed per plan; Trouble Items sorted by time then wrongs.
- YAML export includes all specified fields in English; file named with session timestamp; validated against example.
- Grouped export splits scope into folders with default 12 items; remainder reported; media + WAV copied; optional move toggle gated by warning.
- Persistent settings saved/loaded; Reset to Defaults restores baseline.
- Localization present for all UI strings; switching language updates review UI.
- Non-blocking notifications for minor issues; blocking dialogs only for confirmations/critical errors.

Delegation Notes (for Coding Agent)
- Implement components and wire signals/slots per Architecture.
- Add settings keys and i18n labels; update language switching to refresh review UI.
- Integrate scope-aware buttons for Ocenaudio and single-WAV export to use Review tab’s filtered set.
- Provide unit tests for fairness, YAML, grouped export, and stats; basic UI smoke checks where feasible.

YAML Export Fields
- Overview: Human-readable, English-only, designed for downstream aggregation.
- Top-level keys:
  - version: semantic version of the report format (e.g., "1.0")
  - session:
    - id: UUID or timestamp-based identifier
    - timestamp: ISO-8601 UTC
    - language: UI language code (e.g., en, es)
    - appVersion: app semantic version
  - settings:
    - scope: Images | Videos | Both
    - playCountPerItem: integer
    - timeWeightingPercent: 0–100
    - perItemTimeLimitSec: integer or null
    - limitMode: Soft | Hard
    - uiOverheadMs: integer
    - sfxEnabled: true/false
    - sfxVolumePercent: 0–100
    - sfxTone: Default | Gentle
    - quickConfirmMode: true/false
    - gradingThresholds:
      - Aplus: 0.95
      - A: 0.90
      - Bplus: 0.80
      - B: 0.75
      - Cplus: 0.70
      - C: 0.65
      - D: 0.55
  - randomization:
    - strategy: roundShuffleNoReplacement
    - rounds: integer (derived from playCount)
    - seed: optional integer (if reproducibility is needed)
  - overall:
    - totalItems: integer
    - totalPrompts: integer
    - totalCorrect: integer
    - totalWrong: integer
    - timeouts: integer (hard limit wrongs by expiry)
    - overtimeCount: integer (soft limit expiries)
    - accuracyPercent: float
    - averageTimeSec: float
    - medianTimeSec: float
    - timeEfficiencyScore: 0–1
    - compositeScore: 0–1
    - grade: string (A+, A, B+, B, C+, C, D, F)
  - items: list of per-item results
    - id: stable identifier (e.g., basename)
    - type: image | video
    - label: filename or display name
    - mediaPath: absolute or workspace-relative path
    - wavPath: path to matched recording
    - wrongGuesses: integer
    - timeToCorrectSec: float
    - overtime: true/false
    - timeout: true/false
    - attempts: integer (total confirmations)
    - playCountServed: integer
    - confirmMethod: rightClick | ctrlCmdClick | enter | button
    - notes: optional string
  - troubleItems: ordered list of item ids (longest time, then wrong guesses)
  - environment:
    - os: e.g., macOS
    - platform: e.g., arm64/x86_64
    - pythonVersion: string
    - ffmpegPath: string
    - ffprobePath: string
  - export:
    - groupedMode: itemsPerFolder | numberOfFolders
    - itemsPerFolder: integer (if applicable)
    - numberOfFolders: integer (if applicable)
    - copyOrMove: copy | move
    - remainderInLastFolder: integer

Example YAML
version: "1.0"
session:
  id: "2026-01-10T15:42:21Z-abc123"
  timestamp: "2026-01-10T15:42:21Z"
  language: "en"
  appVersion: "1.8.0"
settings:
  scope: "Both"
  playCountPerItem: 1
  timeWeightingPercent: 30
  perItemTimeLimitSec: null
  limitMode: "Soft"
  uiOverheadMs: 600
  sfxEnabled: true
  sfxVolumePercent: 70
  sfxTone: "Default"
  quickConfirmMode: true
  gradingThresholds:
    Aplus: 0.95
    A: 0.90
    Bplus: 0.80
    B: 0.75
    Cplus: 0.70
    C: 0.65
    D: 0.55
randomization:
  strategy: "roundShuffleNoReplacement"
  rounds: 1
overall:
  totalItems: 12
  totalPrompts: 12
  totalCorrect: 11
  totalWrong: 1
  timeouts: 0
  overtimeCount: 2
  accuracyPercent: 91.67
  averageTimeSec: 2.4
  medianTimeSec: 2.1
  timeEfficiencyScore: 0.84
  compositeScore: 0.91
  grade: "A"
items:
  - id: "apple.jpg"
    type: "image"
    label: "apple.jpg"
    mediaPath: "/path/images/apple.jpg"
    wavPath: "/path/images/apple.jpg.wav"
    wrongGuesses: 0
    timeToCorrectSec: 1.6
    overtime: false
    timeout: false
    attempts: 1
    playCountServed: 1
    confirmMethod: "rightClick"
  - id: "clip1"
    type: "video"
    label: "clip1.mp4"
    mediaPath: "/path/videos/clip1.mp4"
    wavPath: "/path/videos/clip1.wav"
    wrongGuesses: 1
    timeToCorrectSec: 3.2
    overtime: true
    timeout: false
    attempts: 2
    playCountServed: 1
    confirmMethod: "enter"
troubleItems:
  - "clip1"
environment:
  os: "macOS"
  platform: "arm64"
  pythonVersion: "3.11.6"
  ffmpegPath: "/usr/local/bin/ffmpeg"
  ffprobePath: "/usr/local/bin/ffprobe"
export:
  groupedMode: "itemsPerFolder"
  itemsPerFolder: 12
  numberOfFolders: 1
  copyOrMove: "copy"
  remainderInLastFolder: 0
