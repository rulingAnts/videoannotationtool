# Tests

Headless test suite. It drives the **real** Qt widgets under the offscreen platform
plugin (no mocking of the app itself), so it catches real regressions.

## Setup

```bash
pip install pytest PySide6-Essentials opencv-python-headless Pillow pydub numpy PyYAML

# Qt needs these system libraries even offscreen:
apt-get install -y libegl1 libgl1 libxkbcommon0 libdbus-1-3
```

## Running

```bash
export QT_QPA_PLATFORM=offscreen   # also set automatically by tests/conftest.py
python -m pytest tests/ -q
```

## What these tests are for

They are **characterization tests**: they pin down existing behavior so refactoring can
be shown not to change it. Several deliberately assert behavior that is *not* ideal —
those say so in their docstring (e.g.
`test_find_existing_image_audio_stem_fallback_is_a_known_hazard`). If a refactor
intentionally changes such behavior, update the test in the same commit so the change
is a conscious one rather than a silent one.

Test media (small real mp4s via cv2, real images via Pillow, WAVs via `wave`) is
synthesized per-test into a temp folder — see `tests/conftest.py`. The fixture folder
deliberately contains a same-stem `bird.mp4` / `bird.jpg` pair, because stimulus kits
can contain both and their recordings must never collide.

All modal dialogs are stubbed by an autouse fixture, so an unattended run can never
block on a message box.

## Known environment limitations

- **PyAudio is normally unavailable here**, so `PYAUDIO_AVAILABLE` is `False` and real
  playback/recording does not run. These tests cover wiring, control state and file
  naming — **not** audio device behavior. Anything touching real capture still needs a
  manual pass on Windows.
- ffmpeg/ffprobe are usually absent, so conversion paths are not exercised.
