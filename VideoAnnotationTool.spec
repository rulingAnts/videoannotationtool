# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for PySide6-based Visual Stimulus Kit Tool (macOS)

from PyInstaller.utils.hooks import collect_data_files

 # Include i18n YAML overlay
extra_datas = [('vat/i18n/labels.yaml', 'vat/i18n')]

a = Analysis(
    ['videoannotation.py'],
    pathex=[],
    binaries=[('/opt/homebrew/bin/ffmpeg', 'ffmpeg/bin'), ('/opt/homebrew/bin/ffprobe', 'ffmpeg/bin')],
    datas=collect_data_files('PySide6', include_py_files=False) + extra_datas,
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
    name='Visual Stimulus Kit Tool',
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
    icon='assets/icon.icns',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Visual Stimulus Kit Tool',
)
app = BUNDLE(
    coll,
    name='Visual Stimulus Kit Tool.app',
    icon='assets/icon.icns',
    bundle_identifier=None,
)
