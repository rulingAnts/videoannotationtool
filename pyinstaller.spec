# PyInstaller spec for PySide6-based Video Annotation Tool (onefile, windowed build)
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
block_cipher = None

a = Analysis([
    'videoannotation.py'
],
    pathex=[],
    binaries=[],
    datas=collect_data_files('PySide6', include_py_files=False),
    hiddenimports=['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='Video Annotation Tool',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          icon='assets/icon.ico')
