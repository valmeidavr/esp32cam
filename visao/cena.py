"""Desenho do que a camera esta vendo: as pecas rastreadas, a linha de
despejo e a area util da esteira.

Os rotulos saem do rastreador, nao do detector: assim o nome exibido e a
forma mais votada ao longo de toda a passagem da peca, e para de piscar entre
"circulo" e "poligono" quando um quadro sai borrado.
"""

import cv2
import numpy as np

from detector import CORES
from rastreador import Peca

CINZA = (120, 120, 120)
AZUL = (230, 160, 60)


def _rotulo(img, texto: str, x: int, y: int, cor) -> None:
    (largura, altura), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
    # Tarja atras do texto: sem ela o rotulo some sobre fundo claro.
    cv2.rectangle(img, (x - 3, y - altura - 4), (x + largura + 3, y + 3),
                  (0, 0, 0), cv2.FILLED)
    cv2.putText(img, texto, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, cor, 1, cv2.LINE_AA)


def desenhar(quadro: np.ndarray, pecas: list[Peca], linha: int,
             mostrar_linha: bool = True, roi=None,
             mascara: np.ndarray | None = None) -> np.ndarray:
    # Na visao de calibracao a base e a mascara: branco = o que o detector
    # considera peca. Ajuda a acertar os limiares na hora, olhando o resultado.
    if mascara is not None:
        saida = cv2.cvtColor(mascara, cv2.COLOR_GRAY2BGR)
        saida = cv2.addWeighted(saida, 0.75, quadro, 0.25, 0)
    else:
        saida = quadro.copy()
    altura, largura = saida.shape[:2]

    if roi is not None:
        x1, y1, x2, y2 = roi
        # escurece o que esta fora da area util
        sombra = saida.copy()
        sombra[:] = (sombra * 0.35).astype(np.uint8)
        sombra[y1:y2, x1:x2] = saida[y1:y2, x1:x2]
        saida = sombra
        cv2.rectangle(saida, (x1, y1), (x2 - 1, y2 - 1), AZUL, 1)
        _rotulo(saida, "area da esteira", x1 + 4, y1 + 14, AZUL)

    if mostrar_linha:
        # Tracejada, para nao se confundir com a borda de alguma peca.
        for y in range(0, altura, 14):
            cv2.line(saida, (linha, y), (linha, min(y + 8, altura)), (90, 90, 90), 1)
        _rotulo(saida, "despejo", max(2, linha - 58), altura - 8, CINZA)

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
