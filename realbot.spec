# -*- mode: python ; coding: utf-8 -*-

import os
import pathlib
import shutil
import sys

sys.path.append(os.getcwd())
from requirements import update_requirements

update_requirements(ask_for_confirmation=False)

app_name = 'realbot'

# Build realbot.exe
realbot_analysis = Analysis(['realbot.py'], pathex=[], binaries=[],
                            datas=[('sprites', 'sprites'), ('modules/data', 'modules/data')],
                            hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
                            noarchive=False)
realbot_pyz = PYZ(realbot_analysis.pure)
realbot_exe = EXE(realbot_pyz, realbot_analysis.scripts, [], exclude_binaries=True, name=app_name, debug=False,
                  bootloader_ignore_signals=False, strip=False, upx=True, console=True,
                  disable_windowed_traceback=False,
                  argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None)

# Build import.exe
import_analysis = Analysis(['import.py'], pathex=[], binaries=[], datas=[], hiddenimports=[], hookspath=[],
                           hooksconfig={},
                           runtime_hooks=[], excludes=[], noarchive=False)
import_pyz = PYZ(import_analysis.pure)
import_exe = EXE(import_pyz, import_analysis.scripts, [], exclude_binaries=True, name='import', debug=False,
                 bootloader_ignore_signals=False, strip=False, upx=True, console=False,
                 disable_windowed_traceback=False, argv_emulation=False, target_arch=None, codesign_identity=None,
                 entitlements_file=None)

# Put everything in the dist directory
coll = COLLECT(realbot_exe, realbot_analysis.binaries, realbot_analysis.datas,
               import_exe, import_analysis.binaries, import_analysis.datas,
               strip=False, upx=True, upx_exclude=[], name=app_name)

current_dir = pathlib.Path(os.getcwd())
output_dir = pathlib.Path(DISTPATH) / app_name

shutil.copyfile(current_dir / 'LICENSE', output_dir / 'LICENSE.txt')
shutil.copyfile(current_dir / 'README.md', output_dir / 'README.md')

os.mkdir(output_dir / 'profiles')
for file in (current_dir / 'profiles').glob('*.yml'):
    shutil.copyfile(file, output_dir / 'profiles' / file.name)
for file in (current_dir / 'profiles').glob('*.py'):
    shutil.copyfile(file, output_dir / 'profiles' / file.name)

os.mkdir(output_dir / 'roms')
shutil.copyfile(current_dir / 'roms' / '.gitkeep', output_dir / 'roms' / '.gitkeep')
