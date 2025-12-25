#!/usr/bin/env python3.11
"""
Build helper for macOS.

Features:
- Enforces Python 3.11 (this project targets 3.11; newer versions may break deps)
- Optionally (re)generates the PNG/ICO via generate_icon.py and then builds a .icns from PNG
- Runs PyInstaller to create a one-folder, windowed app bundle by default
- Allows toggling console/windowed and onedir/onefile (though onedir is recommended)
 - Optional bundling of ffmpeg/ffprobe binaries into the app so pydub works offline
 - Optional packaging into a .dmg (drag-to-Applications) or .pkg installer

Usage examples:
  python3 scripts/build_mac.py --icon --pyinstaller
  python3 scripts/build_mac.py --pyinstaller --console
    python3 scripts/build_mac.py --pyinstaller --onefile
    python3.11 scripts/build_mac.py --pyinstaller --bundle-ffmpeg
    python3.11 scripts/build_mac.py --pyinstaller --ffmpeg-bin /usr/local/bin/ffmpeg --ffprobe-bin /usr/local/bin/ffprobe
        python3.11 scripts/build_mac.py --pyinstaller --onedir --windowed --dmg
        python3.11 scripts/build_mac.py --pkg --bundle-id com.example.videoannotationtool

Notes:
- .icns is created using macOS tools: `sips` and `iconutil`
- PyInstaller must be installed in your Python 3.11 environment
- Building on macOS produces a .app inside the dist folder when using --windowed
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import importlib.util
import datetime
import json
import plistlib

ROOT = os.path.dirname(os.path.dirname(__file__))
ASSETS_DIR = os.path.join(ROOT, 'assets')
ICON_PNG = os.path.join(ASSETS_DIR, 'icon.png')
ICON_ICNS = os.path.join(ASSETS_DIR, 'icon.icns')
ENTRY = os.path.join(ROOT, 'videoannotation.py')
SETTINGS_FILE = os.path.join(ROOT, '.build_settings.json')
ASSETS_FFMPEG_MAC_DIR = os.path.join(ASSETS_DIR, 'ffmpeg-bin', 'macos')
VERSION_FILE = os.path.join(ROOT, 'VERSION')


def require_python_311():
    if not (sys.version_info.major == 3 and sys.version_info.minor == 11):
        print("[build_mac] ERROR: This build script must be run with Python 3.11.x.")
        print(f"[build_mac] Current Python: {sys.version.split()[0]}")
        print("[build_mac] Tip: Run with python3.11 scripts/build_mac.py ...")
        sys.exit(1)


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def run(cmd, **kwargs):
    cwd = kwargs.get('cwd', os.getcwd())
    print(f"[build_mac] CWD: {cwd}")
    print('[build_mac] >', ' '.join(cmd))
    subprocess.check_call(cmd, **kwargs)


def has_pyinstaller_module() -> bool:
    return importlib.util.find_spec("PyInstaller") is not None


def validate_executable(path: str) -> bool:
    return os.path.isfile(path) and os.access(path, os.X_OK)


def resolve_ffmpeg_bins(ffmpeg_bin: str | None, ffprobe_bin: str | None, auto_discover: bool) -> dict:
    """Return a dict with keys 'ffmpeg' and 'ffprobe' pointing to executable paths, or {} if none."""
    result = {}
    if ffmpeg_bin:
        if os.path.isdir(ffmpeg_bin):
            cand = os.path.join(ffmpeg_bin, 'ffmpeg')
            if validate_executable(cand):
                result['ffmpeg'] = cand
        elif validate_executable(ffmpeg_bin):
            result['ffmpeg'] = ffmpeg_bin
        else:
            print(f"[build_mac] WARNING: --ffmpeg-bin not executable: {ffmpeg_bin}")
    if ffprobe_bin:
        if os.path.isdir(ffprobe_bin):
            cand = os.path.join(ffprobe_bin, 'ffprobe')
            if validate_executable(cand):
                result['ffprobe'] = cand
        elif validate_executable(ffprobe_bin):
            result['ffprobe'] = ffprobe_bin
        else:
            print(f"[build_mac] WARNING: --ffprobe-bin not executable: {ffprobe_bin}")
    if auto_discover:
        if 'ffmpeg' not in result:
            w = which('ffmpeg')
            if w and validate_executable(w):
                result['ffmpeg'] = w
            else:
                # Common Homebrew and local installs
                for cand in ('/opt/homebrew/bin/ffmpeg', '/usr/local/bin/ffmpeg'):
                    if validate_executable(cand):
                        result['ffmpeg'] = cand
                        break
        if 'ffprobe' not in result:
            w = which('ffprobe')
            if w and validate_executable(w):
                result['ffprobe'] = w
            else:
                for cand in ('/opt/homebrew/bin/ffprobe', '/usr/local/bin/ffprobe'):
                    if validate_executable(cand):
                        result['ffprobe'] = cand
                        break
    # Final validation
    if 'ffmpeg' in result and not validate_executable(result['ffmpeg']):
        print(f"[build_mac] WARNING: ffmpeg path not executable: {result['ffmpeg']}")
        result.pop('ffmpeg', None)
    if 'ffprobe' in result and not validate_executable(result['ffprobe']):
        print(f"[build_mac] WARNING: ffprobe path not executable: {result['ffprobe']}")
        result.pop('ffprobe', None)
    if result:
        print("[build_mac] Bundling ff utilities:")
        for k, v in result.items():
            print(f"[build_mac]  - {k}: {v}")
    else:
        print("[build_mac] ffmpeg/ffprobe not provided; will not be bundled.")
    return result


def get_assets_ffmpeg_bins_mac() -> dict:
    """Return ffmpeg/ffprobe from assets/ffmpeg-bin/macos if present."""
    result = {}
    ffmpeg = os.path.join(ASSETS_FFMPEG_MAC_DIR, 'ffmpeg')
    ffprobe = os.path.join(ASSETS_FFMPEG_MAC_DIR, 'ffprobe')
    if validate_executable(ffmpeg):
        result['ffmpeg'] = ffmpeg
    if validate_executable(ffprobe):
        result['ffprobe'] = ffprobe
    return result


def is_universal_binary(path: str) -> bool:
    """Check whether a macOS binary is universal (arm64 + x86_64)."""
    try:
        if not validate_executable(path):
            return False
        out = subprocess.check_output(['lipo', '-info', path], text=True)
        return ('x86_64' in out) and ('arm64' in out)
    except Exception:
        return False


def ensure_png_icon():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    if not os.path.exists(ICON_PNG):
        # Generate icon.png (and .ico) using the existing script
        gen = os.path.join('scripts', 'generate_icon.py')
        print("[build_mac] assets/icon.png not found; generating via scripts/generate_icon.py ...")
        run([sys.executable, gen], cwd=ROOT)
    else:
        print("[build_mac] Using existing icon:", ICON_PNG)


def build_icns_from_png(png_path: str, icns_path: str):
    """Create a .icns from a single large PNG using sips + iconutil."""
    if not os.path.exists(png_path):
        raise FileNotFoundError(f"PNG not found: {png_path}")

    if not which('sips') or not which('iconutil'):
        print("[build_mac] WARNING: 'sips' or 'iconutil' not found; skipping .icns generation.")
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        iconset = os.path.join(tmpdir, 'icon.iconset')
        os.makedirs(iconset, exist_ok=True)
        # Standard macOS icon sizes
        sizes = [16, 32, 64, 128, 256, 512, 1024]
        for sz in sizes:
            out1x = os.path.join(iconset, f'icon_{sz}x{sz}.png')
            run(['sips', '-z', str(sz), str(sz), png_path, '--out', out1x])
            # 2x only for sizes up to 512 (1024x1024 serves as 512@2x)
            if sz <= 512:
                out2x = os.path.join(iconset, f'icon_{sz}x{sz}@2x.png')
                run(['sips', '-z', str(sz*2), str(sz*2), png_path, '--out', out2x])
        # Convert folder to .icns
        run(['iconutil', '-c', 'icns', iconset, '-o', icns_path])
        print('[build_mac] Wrote', icns_path)
        return True


def build_with_pyinstaller(name: str, onedir: bool, windowed: bool, clean: bool, extra_args: list[str] | None = None):
    if not has_pyinstaller_module():
        print("[build_mac] ERROR: PyInstaller is not installed in this Python 3.11 environment.")
        print(f"[build_mac] Install with: {sys.executable} -m pip install pyinstaller")
        sys.exit(1)

    cmd = [sys.executable, '-m', 'PyInstaller']
    if clean:
        cmd.append('--clean')
    # Avoid interactive prompts
    cmd.append('--noconfirm')
    cmd += ['--name', name]
    if onedir:
        cmd.append('--onedir')
    else:
        cmd.append('--onefile')
    if windowed:
        cmd.append('--windowed')
    else:
        cmd.append('--console')

    # Use .icns if we have it; otherwise continue without icon
    if os.path.exists(ICON_ICNS):
        cmd += ['--icon', ICON_ICNS]

    # macOS arm64 silicon-only build
    cmd += ['--target-arch', 'arm64']

        # Hidden imports for PySide6 (hooks already collect necessary Qt frameworks)
    cmd += ['--hidden-import', 'PySide6.QtCore',
            '--hidden-import', 'PySide6.QtGui',
            '--hidden-import', 'PySide6.QtWidgets']

    # Extra args may include add-data/add-binary entries
    if extra_args:
        cmd += extra_args

    cmd.append(ENTRY)
    print("[build_mac] Invoking PyInstaller with:")
    print("[build_mac]  - Python:", sys.executable)
    print("[build_mac]  - onedir:", onedir)
    print("[build_mac]  - windowed:", windowed)
    print("[build_mac]  - clean:", clean)
    if os.path.exists(ICON_ICNS):
        print("[build_mac]  - icon:", ICON_ICNS)
    run(cmd, cwd=ROOT)

    # Post-build: point to likely output
    dist = os.path.join(ROOT, 'dist')
    app_path = os.path.join(dist, f'{name}.app')
    onefile_path = os.path.join(dist, name)
    if onedir and os.path.exists(app_path):
        print(f"[build_mac] Build complete. App bundle: {app_path}")
    elif (not onedir) and os.path.exists(onefile_path):
        print(f"[build_mac] Build complete. Binary: {onefile_path}")
    else:
        print(f"[build_mac] Build complete. Check dist/ for outputs.")

    # Patch Info.plist with version from VERSION file if present
    try:
        if onedir and os.path.exists(app_path) and os.path.exists(VERSION_FILE):
            with open(VERSION_FILE, 'r') as vf:
                version = vf.read().strip()
            info_plist = os.path.join(app_path, 'Contents', 'Info.plist')
            if os.path.exists(info_plist):
                with open(info_plist, 'rb') as f:
                    info = plistlib.load(f)
                # Update version fields
                info['CFBundleShortVersionString'] = version
                info['CFBundleVersion'] = version
                # Ensure privacy usage descriptions are present to allow mic/files access prompts
                info.setdefault('NSMicrophoneUsageDescription', 'Video Annotation Tool needs microphone access to record annotations.')
                info.setdefault('NSDesktopFolderUsageDescription', 'Allow access to Desktop to open and save annotated videos and audio.')
                info.setdefault('NSDocumentsFolderUsageDescription', 'Allow access to Documents to manage project folders, metadata, and recordings.')
                info.setdefault('NSDownloadsFolderUsageDescription', 'Allow access to Downloads to open videos for annotation.')
                info.setdefault('NSNetworkVolumesUsageDescription', 'Allow access to files on network volumes for annotation projects.')
                info.setdefault('NSRemovableVolumesUsageDescription', 'Allow access to external drives (USB/SD) to read/write project media.')
                with open(info_plist, 'wb') as f:
                    plistlib.dump(info, f)
                print(f"[build_mac] Set version to {version} and ensured privacy keys in Info.plist")
    except Exception as e:
        print('[build_mac] WARNING: Failed to patch Info.plist version:', e)


def ensure_app_exists(name: str) -> str:
    dist = os.path.join(ROOT, 'dist')
    app_path = os.path.join(dist, f'{name}.app')
    if not os.path.exists(app_path):
        print(f"[build_mac] ERROR: App bundle not found at {app_path}. Build it first with --pyinstaller.")
        sys.exit(1)
    return app_path


def make_dmg(name: str, volume_name: str | None = None, dmg_name: str | None = None):
    app_path = ensure_app_exists(name)
    dist = os.path.join(ROOT, 'dist')
    volume_name = volume_name or name
    if not dmg_name:
        ts = datetime.datetime.now().strftime('%Y%m%d')
        dmg_name = f"{name}-{ts}.dmg"
    dmg_path = os.path.join(dist, dmg_name)

    staging = os.path.join(dist, f'{name}-dmg-staging')
    if os.path.exists(staging):
        shutil.rmtree(staging)
    os.makedirs(staging, exist_ok=True)
    # Copy .app into staging
    target_app = os.path.join(staging, f'{name}.app')
    print("[build_mac] Staging app for DMG:", target_app)
    run(['cp', '-R', app_path, target_app])
    # Create Applications symlink for drag-and-drop installs
    applications_link = os.path.join(staging, 'Applications')
    if not os.path.exists(applications_link):
        os.symlink('/Applications', applications_link)

    # Create DMG using hdiutil
    print("[build_mac] Creating DMG at:", dmg_path)
    run(['hdiutil', 'create', '-volname', volume_name, '-srcfolder', staging, '-ov', '-format', 'UDZO', dmg_path])
    print("[build_mac] DMG created:", dmg_path)


def make_pkg(name: str, bundle_id: str, install_location: str = '/Applications'):
    app_path = ensure_app_exists(name)
    dist = os.path.join(ROOT, 'dist')
    pkg_path = os.path.join(dist, f'{name}.pkg')
    # pkgbuild wraps the .app into an installer that installs into /Applications by default
    print("[build_mac] Creating PKG at:", pkg_path)
    run([
        'pkgbuild',
        '--install-location', install_location,
        '--component', app_path,
        '--identifier', bundle_id,
        pkg_path
    ])
    print("[build_mac] PKG created:", pkg_path)


def load_settings() -> dict:
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception as e:
        print('[build_mac] WARNING: Failed to load settings:', e)
    return {}


def save_settings(settings: dict):
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        print('[build_mac] Saved settings to', SETTINGS_FILE)
    except Exception as e:
        print('[build_mac] WARNING: Failed to save settings:', e)


def discover_bundle_id_from_app(name: str) -> str | None:
    app_path = os.path.join(ROOT, 'dist', f'{name}.app')
    info_plist = os.path.join(app_path, 'Contents', 'Info.plist')
    if os.path.exists(info_plist):
        try:
            with open(info_plist, 'rb') as f:
                info = plistlib.load(f)
            bid = info.get('CFBundleIdentifier')
            if bid and bid != 'org.pythonmac.unspecified':
                return bid
        except Exception as e:
            print('[build_mac] WARNING: Failed to read Info.plist:', e)
    return None


def main():
    print("[build_mac] Starting macOS build helper...")
    print(f"[build_mac] Python: {sys.version.split()[0]} @ {sys.executable}")
    require_python_311()

    parser = argparse.ArgumentParser()
    parser.add_argument('--icon', action='store_true', help='Generate icon.icns from assets/icon.png (creates PNG via generate_icon.py if missing)')
    parser.add_argument('--pyinstaller', action='store_true', help='Run pyinstaller to produce build')
    parser.add_argument('--onefile', action='store_true', help='Build a single-file executable (not recommended for mac app bundles)')
    parser.add_argument('--onedir', action='store_true', help='Build a one-folder app (default)')
    parser.add_argument('--console', action='store_true', help='Show console when running app')
    parser.add_argument('--windowed', action='store_true', help='Hide console / GUI app (default)')
    parser.add_argument('--name', default='Video Annotation Tool', help='Output app name')
    parser.add_argument('--version', help='Override version (defaults to contents of VERSION file)')
    # Packaging options
    parser.add_argument('--dmg', action='store_true', help='Create a DMG from the built app bundle')
    parser.add_argument('--dmg-name', help='Custom DMG file name (defaults to Name-YYYYMMDD.dmg)')
    parser.add_argument('--volume-name', help='Custom DMG volume name (defaults to app name)')
    parser.add_argument('--pkg', action='store_true', help='Create a PKG installer from the built app bundle')
    parser.add_argument('--bundle-id', help='Bundle identifier (e.g., com.example.videoannotationtool). If omitted, will reuse last value or try to read from built app Info.plist.')
    parser.add_argument('--install-location', default='/Applications', help='Install location for PKG (default /Applications)')
    # FFmpeg bundling options
    parser.add_argument('--bundle-ffmpeg', action='store_true', help='Auto-discover ffmpeg/ffprobe from PATH and bundle them (default for --onedir)')
    parser.add_argument('--no-bundle-ffmpeg', action='store_true', help='Do not bundle ffmpeg/ffprobe (overrides defaults)')
    parser.add_argument('--ffmpeg-bin', help='Path to ffmpeg binary or its containing directory')
    parser.add_argument('--ffprobe-bin', help='Path to ffprobe binary or its containing directory')
    parser.add_argument('--no-clean', action='store_true', help='Do not pass --clean to PyInstaller')
    # Codesigning options for enabling microphone access under Hardened Runtime
    parser.add_argument('--codesign-ad-hoc', action='store_true', help='Codesign the built app with ad-hoc identity and Hardened Runtime')
    parser.add_argument('--codesign-identity', help='Codesign identity to use (e.g., "Developer ID Application: ..."). Defaults to ad-hoc if --codesign-ad-hoc is set.')
    parser.add_argument('--enable-microphone-entitlement', action='store_true', help='Add com.apple.security.device.audio-input entitlement when codesigning')
    parser.add_argument('--entitlements-file', help='Path to a custom entitlements plist to use during codesign')
    args = parser.parse_args()

    did_anything = False

    # Load persisted settings
    settings = load_settings()

    if args.icon:
        did_anything = True
        ensure_png_icon()
        built = build_icns_from_png(ICON_PNG, ICON_ICNS)
        if not built:
            print('Skipping icon embedding (icon.icns not created).')

    if args.pyinstaller:
        did_anything = True
        # Enforce silicon-only onedir, windowed build
        onedir = True
        windowed = True

        # Default behavior: bundle ffmpeg/ffprobe from assets/ffmpeg-bin/macos
        extra_args = []
        bins = get_assets_ffmpeg_bins_mac()
        if not bins:
            print("[build_mac] WARNING: assets/ffmpeg-bin/macos not found or missing executables. Falling back to system auto-discovery.")
            bins = resolve_ffmpeg_bins(args.ffmpeg_bin, args.ffprobe_bin, auto_discover=True)
        # On macOS/Linux, use colon as separator in add-binary SRC:DEST
        dest_dir = 'ffmpeg/bin'
        if 'ffmpeg' in bins:
            extra_args += ['--add-binary', f"{bins['ffmpeg']}:{dest_dir}"]
        if 'ffprobe' in bins:
            extra_args += ['--add-binary', f"{bins['ffprobe']}:{dest_dir}"]

        # If a bundle id was provided (or previously saved), apply it to the built app's Info.plist
        bundle_id_pref = args.bundle_id or settings.get('bundle_id')
        if bundle_id_pref:
            extra_args += ['--osx-bundle-identifier', bundle_id_pref]
            # Persist if provided this run
            if args.bundle_id:
                settings['bundle_id'] = args.bundle_id
                save_settings(settings)

        # Optionally persist version override to VERSION file for this build
        if args.version:
            try:
                with open(VERSION_FILE, 'w') as vf:
                    vf.write(args.version)
                print('[build_mac] Wrote version to VERSION:', args.version)
            except Exception as e:
                print('[build_mac] WARNING: Failed to write VERSION file:', e)

        build_with_pyinstaller(
            name=args.name,
            onedir=onedir,
            windowed=windowed,
            clean=not args.no_clean,
            extra_args=extra_args,
        )

        # Verify presence inside the built app (for onedir bundle)
        if onedir:
            dist = os.path.join(ROOT, 'dist')
            app_path = os.path.join(dist, f'{args.name}.app')
            # Check both Frameworks and Resources locations used by PyInstaller
            frameworks_dir = os.path.join(app_path, 'Contents', 'Frameworks', 'ffmpeg', 'bin')
            resources_dir = os.path.join(app_path, 'Contents', 'Resources', 'ffmpeg', 'bin')
            ffmpeg_inside = os.path.join(frameworks_dir, 'ffmpeg') if os.path.exists(frameworks_dir) else os.path.join(resources_dir, 'ffmpeg')
            ffprobe_inside = os.path.join(frameworks_dir, 'ffprobe') if os.path.exists(frameworks_dir) else os.path.join(resources_dir, 'ffprobe')
            print("[build_mac] Verifying embedded ffmpeg paths:")
            print("[build_mac]  ", ffmpeg_inside, 'OK' if os.path.exists(ffmpeg_inside) else 'MISSING')
            print("[build_mac]  ", ffprobe_inside, 'OK' if os.path.exists(ffprobe_inside) else 'MISSING')
            if not os.path.exists(ffmpeg_inside):
                print("[build_mac] NOTE: ffmpeg not found in app bundle. Ensure assets/ffmpeg-bin/macos contains 'ffmpeg'.")
            else:
                # Ensure execute permissions
                try:
                    st = os.stat(ffmpeg_inside)
                    os.chmod(ffmpeg_inside, st.st_mode | 0o111)
                    print("[build_mac] Ensured execute permissions on:", ffmpeg_inside)
                except Exception as e:
                    print("[build_mac] WARNING: Could not chmod +x on ffmpeg:", e)
                # Check universal fat binary
                if not is_universal_binary(ffmpeg_inside):
                    print("[build_mac] WARNING: ffmpeg in bundle is not a universal binary (arm64 + x86_64).")
            if os.path.exists(ffprobe_inside):
                try:
                    st = os.stat(ffprobe_inside)
                    os.chmod(ffprobe_inside, st.st_mode | 0o111)
                    print("[build_mac] Ensured execute permissions on:", ffprobe_inside)
                except Exception as e:
                    print("[build_mac] WARNING: Could not chmod +x on ffprobe:", e)
                if not is_universal_binary(ffprobe_inside):
                    print("[build_mac] WARNING: ffprobe in bundle is not a universal binary.")

        # Optional codesign step to enable Hardened Runtime with microphone entitlement
        if args.codesign_ad_hoc or args.codesign_identity:
            identity = args.codesign_identity if args.codesign_identity else "-"
            app_path = os.path.join(ROOT, 'dist', f'{args.name}.app')
            if os.path.exists(app_path):
                ent_plist = None
                if args.entitlements_file and os.path.exists(args.entitlements_file):
                    ent_plist = args.entitlements_file
                elif args.enable_microphone_entitlement:
                    # Generate a minimal entitlements file in a temp dir
                    try:
                        import tempfile
                        ent_plist = os.path.join(tempfile.gettempdir(), 'vat-entitlements.plist')
                        ent = {
                            'com.apple.security.device.audio-input': True,
                            'com.apple.security.files.user-selected.read-write': True,
                            'com.apple.security.cs.disable-library-validation': True,
                        }
                        with open(ent_plist, 'wb') as f:
                            plistlib.dump(ent, f)
                        print('[build_mac] Generated entitlements:', ent_plist)
                    except Exception as e:
                        print('[build_mac] WARNING: Failed to generate entitlements plist:', e)
                        ent_plist = None
                try:
                    cmd = ['codesign', '--force', '--deep', '--options', 'runtime']
                    if ent_plist:
                        cmd += ['--entitlements', ent_plist]
                    cmd += ['--sign', identity, app_path]
                    print('[build_mac] Codesigning app with identity:', identity)
                    run(cmd)
                    # Verify
                    run(['codesign', '-dv', '--verbose=4', app_path])
                    print('[build_mac] Codesign completed.')
                except Exception as e:
                    print('[build_mac] WARNING: Codesign failed:', e)

    # Post-build packaging
    if args.dmg:
        did_anything = True
        make_dmg(name=args.name, volume_name=args.volume_name, dmg_name=args.dmg_name)

    if args.pkg:
        did_anything = True
        # Resolve bundle id preference: CLI > saved settings > Info.plist > fallback error
        bundle_id = args.bundle_id or settings.get('bundle_id') or discover_bundle_id_from_app(args.name)
        if not bundle_id:
            print('[build_mac] ERROR: No bundle identifier found. Provide --bundle-id once; it will be remembered for next runs.')
            sys.exit(1)
        else:
            # Persist for future runs if provided this time
            if args.bundle_id:
                settings['bundle_id'] = args.bundle_id
                save_settings(settings)
        make_pkg(name=args.name, bundle_id=bundle_id, install_location=args.install_location)

    if not did_anything:
        print("[build_mac] No actions requested. Use one or more flags:")
        print("[build_mac]   --icon         Generate/refresh assets/icon.icns from assets/icon.png")
        print("[build_mac]   --pyinstaller  Build the app with PyInstaller")
        print("[build_mac] Optional toggles:")
        print("[build_mac]   --onefile | --onedir (default onedir)")
        print("[build_mac]   --console | --windowed (default windowed)")
        print("[build_mac] Packaging:")
        print("[build_mac]   --dmg [--dmg-name NAME.dmg] [--volume-name VOL]  Create DMG")
        print("[build_mac]   --pkg [--bundle-id com.example.app] [--install-location /Applications]")
        print("[build_mac]      Note: bundle id is remembered across runs and auto-read from built app Info.plist when possible.")
        print("[build_mac] Example:")
        print("[build_mac]   python3.11 scripts/build_mac.py --icon --pyinstaller")


if __name__ == '__main__':
    main()
