"""Regravacao do firmware na ESP32-CAM, a partir do binario que acompanha o
programa.

Serve para o caso de a banca usar outra placa, ou de a placa ter sido
regravada com outra coisa. Chamado por `app.py --gravar`.
"""

import os
import sys

BINARIO = "esp32cam-formas.bin"


def caminho_do_binario() -> str | None:
    """Acha o .bin tanto rodando pelo Python quanto dentro do .exe.

    O PyInstaller descompacta os arquivos extras numa pasta temporaria cujo
    caminho fica em sys._MEIPASS; fora dele, o .bin esta ao lado do fonte.
    """
    bases = []
    if hasattr(sys, "_MEIPASS"):
        bases.append(os.path.join(sys._MEIPASS, "firmware"))
    aqui = os.path.dirname(os.path.abspath(__file__))
    bases += [os.path.join(aqui, "firmware"), aqui]

    for base in bases:
        caminho = os.path.join(base, BINARIO)
        if os.path.isfile(caminho):
            return caminho
    return None


def gravar(porta: str) -> bool:
    binario = caminho_do_binario()
    if binario is None:
        print(f"nao encontrei {BINARIO} junto do programa.")
        return False

    print(f"\ngravando {os.path.basename(binario)} em {porta}...")
    print("(nao desligue o cabo durante a gravacao)\n")

    import esptool

    try:
        esptool.main([
            "--chip", "esp32",
            "--port", porta,
            "--baud", "460800",
            "write-flash",
            "-z",                     # comprime, fica bem mais rapido
            "--flash-mode", "dio",
            "--flash-freq", "40m",
            "--flash-size", "4MB",
            "0x0", binario,
        ])
    except SystemExit as saida:
        # esptool encerra com sys.exit; so o codigo 0 e sucesso.
        if saida.code not in (0, None):
            print("\na gravacao falhou.")
            print("  - se a placa for a versao 'nua' (sem o shield preto),")
            print("    ligue GPIO0 no GND, aperte RESET e tente de novo.")
            return False
    except Exception as erro:
        print(f"\na gravacao falhou: {erro}")
        return False

    print("\nfirmware gravado. Pode rodar o programa normalmente.")
    return True
