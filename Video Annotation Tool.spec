# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/Users/Seth/GIT/videoannotationtool/videoannotation.py'],
    pathex=[],
    binaries=[('/opt/homebrew/bin/ffmpeg', 'ffmpeg/bin'), ('/opt/homebrew/bin/ffprobe', 'ffmpeg/bin')],
    datas=[],
    hiddenimports=['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets'],
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
    name='Video Annotation Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
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
    name='Video Annotation Tool',
)
app = BUNDLE(
    coll,
    name='Video Annotation Tool.app',
    icon='/Users/Seth/GIT/videoannotationtool/assets/icon.icns',
    bundle_identifier=None,
)
