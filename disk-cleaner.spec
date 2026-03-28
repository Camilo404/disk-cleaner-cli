# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import sys
import os

block_cipher = None

# Get Python directory
python_dir = os.path.dirname(sys.executable)
python_dll = os.path.join(python_dir, 'python314.dll')

a = Analysis(
    ['src\\disk_cleaner\\__main__.py'],
    pathex=[],
    binaries=[
        (python_dll, '.'),
    ],
    datas=[],
    hiddenimports=[
        'ctypes',
        'click',
        'tqdm',
        'disk_cleaner',
        'disk_cleaner.cli',
        'disk_cleaner.cleaner',
        'disk_cleaner.scanner',
        'disk_cleaner.locations',
        'disk_cleaner.locations_extended',
        'disk_cleaner.utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pandas',
        'matplotlib',
        'matplotlib.pyplot',
        'numpy',
        'PIL',
        'PIL.Image',
        'PIL.ImageFilter',
        'PIL.SpiderImagePlugin',
        'tkinter',
        'Cryptography',
        'OpenSSL',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    exclude_binaries=False,
    name='disk-cleaner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    icon='C:\\Users\\Innovati-3\\Documents\\Projects\\disk-cleaner-cli\\icon.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
