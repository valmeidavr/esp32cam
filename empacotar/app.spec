# -*- mode: python -*-
# Receita do PyInstaller: transforma visao/ num programa Windows que roda sem
# Python instalado. Gerado em "one-dir" (uma pasta com o .exe e as DLLs) de
# proposito: abre mais rapido que o "one-file", que descompacta 100 MB no
# %TEMP% a cada clique.

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

RAIZ = os.path.abspath(os.path.join(SPECPATH, ".."))
VISAO = os.path.join(RAIZ, "visao")

a = Analysis(
    [os.path.join(VISAO, "app.py")],
    pathex=[VISAO],
    binaries=[],
    datas=[
        # o firmware acompanha o programa, para o "--gravar" funcionar em
        # qualquer PC sem precisar do PlatformIO
        (os.path.join(VISAO, "firmware", "esp32cam-formas.bin"), "firmware"),
        # o esptool carrega os "stub flashers" de arquivos JSON dentro do
        # pacote; sem eles a gravacao falha com "Flasher stub data is missing"
        *collect_data_files("esptool"),
    ],
    hiddenimports=[
        "serial.tools.list_ports",
        "serial.tools.list_ports_windows",
        *collect_submodules("esptool"),
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PyQt5", "PySide2", "IPython"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ClassificadorESP32CAM",
    icon=os.path.join(SPECPATH, "icone.ico"),
    debug=False,
    strip=False,
    upx=False,
    console=True,        # a janela preta mostra o endereco e os erros
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ClassificadorESP32CAM",
)
