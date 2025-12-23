Build instructions for Windows onefile, windowed executable and NSIS installer

## PySide6 Migration Notice

The application has been migrated from Tkinter to PySide6 (Qt for Python) for improved stability on macOS and Windows.

Prereqs
- Python 3.11+ (tested with 3.11 and 3.12)
- pip install PySide6 pillow pyinstaller
- On Windows: install NSIS (makensis) to compile the .nsi installer
- On Linux: install Qt system dependencies (libgl1-mesa-glx libegl1 libxkbcommon-x11-0)

Quick steps

1. Generate the icon files (PNG + ICO):

   python scripts/generate_icon.py

   This writes `assets/icon.png` and `assets/icon.ico`.

2. Build the one-file, windowed executable using PyInstaller:

   pyinstaller --clean pyinstaller.spec

   The spec points to `assets/icon.ico` and produces `dist/VideoAnnotationTool.exe`.
   
   Note: PyInstaller will automatically include PySide6 Qt plugins (platforms, imageformats) 
   using the collect_data_files hook in the spec.

3. Create the NSIS installer (on Windows):

   makensis installer/videoannotation_installer.nsi

Notes
- Cross-building Windows executables on macOS is non-trivial. For reliable results, run the PyInstaller step on Windows or use a CI runner with Windows.
- The icon was generated programmatically to convey video (film strip), audio (waveform), and linguistic elicitation (speech bubble). You can replace `assets/icon.png` with a custom design if you prefer.
- PySide6 requires Qt plugins to be included in the build. The updated spec files handle this automatically.
