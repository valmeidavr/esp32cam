"""Descoberta automatica da porta em que a ESP32-CAM esta ligada.

Numa apresentacao ninguem quer abrir o Gerenciador de Dispositivos para
descobrir se a placa caiu em COM3 ou COM7 — o numero muda de PC para PC e ate
de porta USB para porta USB no mesmo PC.
"""

from serial.tools import list_ports

# Conversores USB-serial usados nas placas ESP32-CAM. O CH340 e o do shield
# "ESP32-CAM-MB"; os outros aparecem em adaptadores avulsos e clones.
CHIPS_CONHECIDOS = {
    (0x1A86, 0x7523): "CH340",
    (0x1A86, 0x55D4): "CH9102",
    (0x10C4, 0xEA60): "CP2102",
    (0x0403, 0x6001): "FT232",
    (0x303A, 0x1001): "ESP32-S3 (USB nativo)",
}


def listar_candidatas() -> list[tuple[str, str]]:
    """Portas que parecem ser uma ESP32, como (porta, descricao)."""
    achadas = []
    for p in list_ports.comports():
        chip = CHIPS_CONHECIDOS.get((p.vid, p.pid))
        if chip:
            achadas.append((p.device, f"{chip} em {p.device}"))
    return achadas


def listar_todas() -> list[tuple[str, str]]:
    """Todas as seriais do sistema — usado so para a mensagem de erro."""
    return [(p.device, f"{p.device} — {p.description}") for p in list_ports.comports()]


def encontrar(preferida: str | None = None) -> tuple[str | None, str]:
    """Escolhe a porta a usar.

    Devolve (porta, explicacao). A porta vem None quando nao da para decidir
    sozinho, e a explicacao e o que mostrar para a pessoa.
    """
    if preferida:
        return preferida, f"usando a porta indicada: {preferida}"

    candidatas = listar_candidatas()

    if len(candidatas) == 1:
        porta, descricao = candidatas[0]
        return porta, f"ESP32-CAM encontrada: {descricao}"

    if len(candidatas) > 1:
        # Mais de um conversor ligado: nao da para adivinhar qual e a camera.
        nomes = ", ".join(p for p, _ in candidatas)
        return candidatas[0][0], (
            f"achei mais de uma placa ({nomes}); usando {candidatas[0][0]}. "
            f"Se for a errada, rode com --porta COMx"
        )

    todas = listar_todas()
    if todas:
        return None, (
            "nao achei nenhuma ESP32-CAM. Portas disponiveis: "
            + "; ".join(d for _, d in todas)
            + ". Ligue a placa pelo cabo USB (um cabo de dados, nao so de carga)."
        )

    return None, (
        "nenhuma porta serial no sistema. Ligue a ESP32-CAM pelo cabo USB. "
        "Se ela estiver ligada e mesmo assim nao aparecer, falta o driver do "
        "conversor CH340."
    )
