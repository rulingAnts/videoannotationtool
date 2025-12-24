"""
Windows build helper: generate icon, run PyInstaller (onefile or onedir),
optionally bundle ffmpeg/ffprobe, and validate NSIS script.

Usage examples:
  python3 scripts/build_windows.py --icon --pyinstaller
  python3 scripts/build_windows.py --pyinstaller --onefile
  python3 scripts/build_windows.py --pyinstaller --onedir --bundle-ffmpeg
  python3 scripts/build_windows.py --pyinstaller --ffmpeg-bin C:\\ffmpeg\\bin\\ffmpeg.exe --ffprobe-bin C:\\ffmpeg\\bin\\ffprobe.exe
"""
import argparse
import subprocess
import sys
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(__file__))
ENTRY = os.path.join(ROOT, 'videoannotation.py')
ASSETS_DIR = os.path.join(ROOT, 'assets')
ICON_PNG = os.path.join(ASSETS_DIR, 'icon.png')
ICON_ICO = os.path.join(ASSETS_DIR, 'icon.ico')
ASSETS_FFMPEG_WIN_DIR = os.path.join(ASSETS_DIR, 'ffmpeg-bin', 'windows')


def run(cmd, **kwargs):
    print('>', ' '.join(cmd))
    subprocess.check_call(cmd, **kwargs)


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def validate_executable(path: str) -> bool:
    return os.path.isfile(path) and os.access(path, os.X_OK)


def resolve_ffmpeg_bins(ffmpeg_bin: str | None, ffprobe_bin: str | None, auto_discover: bool) -> dict:
    """Return dict with 'ffmpeg' and 'ffprobe' Windows executable paths if found."""
    result = {}
    # Explicit paths or containing directories
    if ffmpeg_bin:
        if os.path.isdir(ffmpeg_bin):
            cand = os.path.join(ffmpeg_bin, 'ffmpeg.exe')
            if validate_executable(cand):
                result['ffmpeg'] = cand
        elif validate_executable(ffmpeg_bin):
            result['ffmpeg'] = ffmpeg_bin
    if ffprobe_bin:
        if os.path.isdir(ffprobe_bin):
            cand = os.path.join(ffprobe_bin, 'ffprobe.exe')
            if validate_executable(cand):
                result['ffprobe'] = cand
        elif validate_executable(ffprobe_bin):
            result['ffprobe'] = ffprobe_bin
    # Auto-discover on PATH or common install locations
    if auto_discover:
        if 'ffmpeg' not in result:
            w = which('ffmpeg.exe') or which('ffmpeg')
            if w and validate_executable(w):
                result['ffmpeg'] = w
            else:
                for cand in (
                    'C:\\ffmpeg\\bin\\ffmpeg.exe',
                    'C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe',
                    'C:\\Program Files (x86)\\ffmpeg\\bin\\ffmpeg.exe',
                ):
                    if validate_executable(cand):
                        result['ffmpeg'] = cand
                        break
        if 'ffprobe' not in result:
            w = which('ffprobe.exe') or which('ffprobe')
            if w and validate_executable(w):
                result['ffprobe'] = w
            else:
                for cand in (
                    'C:\\ffmpeg\\bin\\ffprobe.exe',
                    'C:\\Program Files\\ffmpeg\\bin\\ffprobe.exe',
                    'C:\\Program Files (x86)\\ffmpeg\\bin\\ffprobe.exe',
                ):
                    if validate_executable(cand):
                        result['ffprobe'] = cand
                        break
    return result


def get_assets_ffmpeg_bins_win() -> dict:
    """Return ffmpeg/ffprobe from assets/ffmpeg-bin/windows if present."""
    result = {}
    ffmpeg = os.path.join(ASSETS_FFMPEG_WIN_DIR, 'ffmpeg.exe')
    ffprobe = os.path.join(ASSETS_FFMPEG_WIN_DIR, 'ffprobe.exe')
    if validate_executable(ffmpeg):
        result['ffmpeg'] = ffmpeg
    if validate_executable(ffprobe):
        result['ffprobe'] = ffprobe
    return result


def ensure_icon():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    # Generate PNG/ICO if missing using existing script
    if not os.path.exists(ICON_PNG) or not os.path.exists(ICON_ICO):
        run([sys.executable, os.path.join('scripts', 'generate_icon.py')], cwd=ROOT)


def build_with_pyinstaller(name: str, onefile: bool, windowed: bool, clean: bool, extra_args: list[str] | None = None):
    cmd = ['pyinstaller']
    if clean:
        cmd.append('--clean')
    cmd += ['--name', name]
    cmd += ['--icon', ICON_ICO] if os.path.exists(ICON_ICO) else []
    cmd += ['--onefile'] if onefile else ['--onedir']
    cmd += ['--windowed'] if windowed else ['--console']

    # Hidden imports and PySide6 resources
    cmd += ['--hidden-import', 'PySide6.QtCore',
            '--hidden-import', 'PySide6.QtGui',
            '--hidden-import', 'PySide6.QtWidgets']
    cmd += ['--collect-all', 'PySide6']

    if extra_args:
        cmd += extra_args

    cmd.append(ENTRY)
    run(cmd, cwd=ROOT)

    dist = os.path.join(ROOT, 'dist')
    out_path = os.path.join(dist, name + ('.exe' if onefile else ''))
    bundle_dir = os.path.join(dist, name) if not onefile else dist
    print('[build_windows] Build complete. Dist:', dist)
    if os.path.exists(out_path):
        print('[build_windows] Binary:', out_path)
    elif not onefile and os.path.exists(bundle_dir):
        print('[build_windows] Onedir:', bundle_dir)
        # Verify embedded ffmpeg paths inside onedir bundle
        ff_dir = os.path.join(bundle_dir, 'ffmpeg', 'bin')
        ffmpeg_inside = os.path.join(ff_dir, 'ffmpeg.exe')
        ffprobe_inside = os.path.join(ff_dir, 'ffprobe.exe')
        print('[build_windows] Verifying embedded ffmpeg paths:')
        print('[build_windows]  ', ffmpeg_inside, 'OK' if os.path.exists(ffmpeg_inside) else 'MISSING')
        print('[build_windows]  ', ffprobe_inside, 'OK' if os.path.exists(ffprobe_inside) else 'MISSING')
        if not os.path.exists(ffmpeg_inside):
            print('[build_windows] NOTE: ffmpeg.exe not found in bundle. Ensure assets/ffmpeg-bin/windows contains ffmpeg.exe.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--icon', action='store_true', help='Generate assets/icon.png and .ico')
    parser.add_argument('--pyinstaller', action='store_true', help='Run PyInstaller to produce build')
    parser.add_argument('--onefile', action='store_true', help='Build single-file executable')
    parser.add_argument('--onedir', action='store_true', help='Build one-folder app')
    parser.add_argument('--console', action='store_true', help='Console build')
    parser.add_argument('--windowed', action='store_true', help='Windowed build (GUI)')
    parser.add_argument('--no-clean', action='store_true', help='Do not pass --clean to PyInstaller')
    # FFmpeg bundling options
    # FFmpeg bundling is now default from assets/ffmpeg-bin/windows
    parser.add_argument('--ffmpeg-bin', help='Override path to ffmpeg.exe or containing directory (optional)')
    parser.add_argument('--ffprobe-bin', help='Override path to ffprobe.exe or containing directory (optional)')
    # NSIS
    parser.add_argument('--nsis', action='store_true', help='Validate NSIS script presence')
    args = parser.parse_args()

    if args.icon:
        ensure_icon()

    if args.pyinstaller:
        onefile = True if args.onefile else False
        if args.onedir:
            onefile = False
        windowed = True if args.windowed else True  # default windowed
        if args.console:
            windowed = False

        extra_args = []
        # Default: bundle from assets
        bins = get_assets_ffmpeg_bins_win()
        if not bins:
            print('[build_windows] WARNING: assets/ffmpeg-bin/windows not found or missing executables. Falling back to PATH auto-discovery.')
            bins = resolve_ffmpeg_bins(args.ffmpeg_bin, args.ffprobe_bin, auto_discover=True)
        # Windows uses ';' separator for --add-binary SRC;DEST
        dest_dir = 'ffmpeg\\bin'
        if 'ffmpeg' in bins:
            extra_args += ['--add-binary', f"{bins['ffmpeg']};{dest_dir}"]
        if 'ffprobe' in bins:
            extra_args += ['--add-binary', f"{bins['ffprobe']};{dest_dir}"]

        build_with_pyinstaller(
            name='Video Annotation Tool',
            onefile=onefile,
            windowed=windowed,
            clean=not args.no_clean,
            extra_args=extra_args,
        )

    if args.nsis:
        nsis = os.path.join(ROOT, 'installer', 'videoannotation_installer.nsi')
        if os.path.exists(nsis):
            print('[build_windows] NSIS script ready:', nsis)
        else:
            print('[build_windows] No NSIS script found at', nsis)


if __name__ == '__main__':
    main()
