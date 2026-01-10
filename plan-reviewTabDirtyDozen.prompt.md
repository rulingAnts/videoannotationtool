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
