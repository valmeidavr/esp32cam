"""Descoberta do endereco da maquina na rede local."""

import socket


def ip_local() -> str | None:
    """IP com que os outros aparelhos da rede enxergam este PC.

    O truque do socket UDP nao envia pacote nenhum: so pergunta ao sistema
    qual placa de rede ele usaria para falar com a internet, o que resolve o
    caso de o PC ter varias (Wi-Fi, cabo, VPN, adaptador virtual).
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()
