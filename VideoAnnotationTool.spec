# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/Users/Seth/GIT/videoannotationtool/./videoannotation.py'],
    pathex=[],
    binaries=[('/opt/homebrew/bin/ffmpeg', 'ffmpeg/bin'), ('/opt/homebrew/bin/ffprobe', 'ffmpeg/bin')],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VideoAnnotationTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['/Users/Seth/GIT/videoannotationtool/assets/icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VideoAnnotationTool',
)
app = BUNDLE(
    coll,
    name='VideoAnnotationTool.app',
    icon='/Users/Seth/GIT/videoannotationtool/./assets/icon.icns',
    bundle_identifier=None,
)
