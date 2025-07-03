# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ("./demo.yaml", "."),
        ("./config.json", "."),
        ("./unimernet/configs", "unimernet/configs"),
        ("./models/unimernet_small/*.json", "models/unimernet_small"),
        ("./models/unimernet_small/*.pth", "models/unimernet_small"),
        (".venv/lib/python3.10/site-packages/transformers/models/gemma2", "transformers/models/gemma2"),
        ("libs/katex", "libs/katex")
    ],
    hiddenimports=[
        "unimernet",
    ],
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
    name='FreeTex',  # The name of the executable
    icon='resources/images/icon.ico',
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FreeTex',
)

app = BUNDLE(
    coll,
    name='FreeTeX.app',
    icon='images/icon.icns',
    bundle_identifier=None,
)