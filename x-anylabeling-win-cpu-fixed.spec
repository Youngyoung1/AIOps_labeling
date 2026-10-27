# -*- mode: python -*-
# vim: ft=python
# Windows CPU 빌드용 (원본 spec의 macOS 잔재 제거 + .ico 아이콘 + 폴더형 배포)

import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

sys.setrecursionlimit(5000)

hidden = (
    collect_submodules('anylabeling')
    + collect_submodules('onnxruntime')
    + ['qimage2ndarray', 'shapely', 'shapely.geometry']
)

datas = [
    ('anylabeling/configs/auto_labeling/*.yaml', 'anylabeling/configs/auto_labeling'),
    ('anylabeling/configs/*.yaml', 'anylabeling/configs'),
    ('anylabeling/views/labeling/widgets/auto_labeling/auto_labeling.ui', 'anylabeling/views/labeling/widgets/auto_labeling'),
    ('anylabeling/services/auto_labeling/configs', 'anylabeling/services/auto_labeling/configs'),
    ('anylabeling/resources', 'anylabeling/resources'),
]

a = Analysis(
    ['anylabeling/app.py'],
    pathex=['anylabeling'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'matplotlib', 'ultralytics'],
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='X-AnyLabeling-CPU',
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon='anylabeling/resources/images/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='X-AnyLabeling-CPU',
)
