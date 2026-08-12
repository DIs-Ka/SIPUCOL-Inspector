# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\Admin\\Projects\\Inspector-Sipucol\\desktop-clean-stage\\backend_entry.py'],
    pathex=['C:\\Users\\Admin\\Projects\\Inspector-Sipucol\\desktop-clean-stage'],
    binaries=[],
    datas=[('C:\\Users\\Admin\\Projects\\Inspector-Sipucol\\desktop-clean-stage\\backend', 'backend'), ('C:\\Users\\Admin\\Projects\\Inspector-Sipucol\\desktop-clean-stage\\manuals', 'manuals')],
    hiddenimports=['tkinter', 'tkinter.filedialog', 'uvicorn.logging', 'uvicorn.loops.auto', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan.on', 'backend.pdf_clean_final_override', 'backend.pdf_final_page_filter_worker'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'scipy', 'pandas', 'pyarrow', 'matplotlib', 'sklearn', 'nltk'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='InspectorSipucolBackend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory='_internal',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='InspectorSipucolBackend',
)
