"""
Helper to: generate icon, run PyInstaller to build a one-file, windowed executable,
and optionally prepare an NSIS installer script.

Usage:
  python3 scripts/build_windows.py --icon --pyinstaller

This script assumes you have PyInstaller and Pillow installed in your build environment.
On macOS/Linux you can still build the spec but cross-building Windows executables
typically requires running on Windows or using wine.
"""
import argparse
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.dirname(__file__))

def run(cmd, **kwargs):
    print('>', ' '.join(cmd))
    subprocess.check_call(cmd, **kwargs)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--icon', action='store_true', help='Generate assets/icon.png and .ico')
    parser.add_argument('--pyinstaller', action='store_true', help='Run pyinstaller to produce onefile exe')
    parser.add_argument('--nsis', action='store_true', help='Validate NSIS script presence')
    args = parser.parse_args()

    if args.icon:
        run([sys.executable, os.path.join('scripts', 'generate_icon.py')], cwd=ROOT)

    if args.pyinstaller:
        # Use the included spec
        spec = os.path.join(ROOT, 'pyinstaller.spec')
        run(['pyinstaller', '--clean', spec], cwd=ROOT)

    if args.nsis:
        nsis = os.path.join(ROOT, 'installer', 'videoannotation_installer.nsi')
        if os.path.exists(nsis):
            print('NSIS script ready:', nsis)
        else:
            print('No NSIS script found at', nsis)

if __name__ == '__main__':
    main()
