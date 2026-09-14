"""Desenho do que a camera esta vendo: as pecas rastreadas e a linha de
despejo.

Os rotulos saem do rastreador, nao do detector: assim o nome exibido e a
forma mais votada ao longo de toda a passagem da peca, e para de piscar entre
"circulo" e "poligono" quando um quadro sai borrado.
"""

import cv2
import numpy as np

from detector import CORES
from rastreador import Peca

BRANCO = (255, 255, 255)
CINZA = (120, 120, 120)


def _rotulo(img, texto: str, x: int, y: int, cor) -> None:
    (largura, altura), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
    # Tarja atras do texto: sem ela o rotulo some sobre fundo claro.
    cv2.rectangle(img, (x - 3, y - altura - 4), (x + largura + 3, y + 3),
                  (0, 0, 0), cv2.FILLED)
    cv2.putText(img, texto, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, cor, 1, cv2.LINE_AA)


def desenhar(quadro: np.ndarray, pecas: list[Peca], linha: int,
             mostrar_linha: bool = True) -> np.ndarray:
    saida = quadro.copy()
    altura, largura = saida.shape[:2]

    if mostrar_linha:
        # Tracejada, para nao se confundir com a borda de alguma peca.
        for y in range(0, altura, 14):
            cv2.line(saida, (linha, y), (linha, min(y + 8, altura)), (90, 90, 90), 1)
        _rotulo(saida, "despejo", max(2, linha - 58), 14, CINZA)

    for peca in pecas:
        cor = CORES.get(peca.nome, (200, 200, 200))

        if peca.contorno is not None:
            cv2.drawContours(saida, [peca.contorno], -1, cor, 2)

        cx, cy = peca.centro
        cv2.circle(saida, (cx, cy), 3, cor, cv2.FILLED)

        texto = f"#{peca.id} {peca.nome}"
        if peca.contada:
            texto += " *"          # ja caiu no compartimento
        _rotulo(saida, texto, max(2, cx - 40), max(12, cy - 10), cor)

    return saida
