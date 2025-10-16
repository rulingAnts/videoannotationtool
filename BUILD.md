Build instructions for Windows onefile, windowed executable and NSIS installer

Prereqs
- Python 3.8+ - 3.11 (will not work on Python newer than 3.11 because of packages no longer available)
- pip install pillow pyinstaller
- On Windows: install NSIS (makensis) to compile the .nsi installer

Quick steps

1. Generate the icon files (PNG + ICO):

   python scripts/generate_icon.py

   This writes `assets/icon.png` and `assets/icon.ico`.

2. Build the one-file, windowed executable using PyInstaller:

   pyinstaller --clean pyinstaller.spec

   The spec points to `assets/icon.ico` and produces `dist/VideoAnnotationTool.exe`.

3. Create the NSIS installer (on Windows):

   makensis installer/videoannotation_installer.nsi

Notes
- Cross-building Windows executables on macOS is non-trivial. For reliable results, run the PyInstaller step on Windows or use a CI runner with Windows.
- The icon was generated programmatically to convey video (film strip), audio (waveform), and linguistic elicitation (speech bubble). You can replace `assets/icon.png` with a custom design if you prefer.
