# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = [('C:\\Users\\Seth\\Windows File System Folder\\GIT\\videoannotationtool\\assets\\ffmpeg-bin\\windows\\ffmpeg.exe', 'ffmpeg\\bin'), ('C:\\Users\\Seth\\Windows File System Folder\\GIT\\videoannotationtool\\assets\\ffmpeg-bin\\windows\\ffprobe.exe', 'ffmpeg\\bin')]
hiddenimports = ['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets']
tmp_ret = collect_all('PySide6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:\\Users\\Seth\\Windows File System Folder\\GIT\\videoannotationtool\\videoannotation.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\Seth\\Windows File System Folder\\GIT\\videoannotationtool\\assets\\icon.ico'],
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
