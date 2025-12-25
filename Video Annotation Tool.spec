# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/Users/Seth/GIT/videoannotationtool/videoannotation.py'],
    pathex=[],
    binaries=[('/Users/Seth/GIT/videoannotationtool/assets/ffmpeg-bin/macos/ffmpeg', 'ffmpeg/bin'), ('/Users/Seth/GIT/videoannotationtool/assets/ffmpeg-bin/macos/ffprobe', 'ffmpeg/bin')],
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
    info_plist={
        'NSMicrophoneUsageDescription': 'Video Annotation Tool needs microphone access to record annotations.',
        'NSDesktopFolderUsageDescription': 'Allow access to Desktop to open and save annotated videos and audio.',
        'NSDocumentsFolderUsageDescription': 'Allow access to Documents to manage project folders, metadata, and recordings.',
        'NSDownloadsFolderUsageDescription': 'Allow access to Downloads to open videos for annotation.',
        'NSNetworkVolumesUsageDescription': 'Allow access to files on network volumes for annotation projects.',
        'NSRemovableVolumesUsageDescription': 'Allow access to external drives (USB/SD) to read/write project media.',
    },
)
