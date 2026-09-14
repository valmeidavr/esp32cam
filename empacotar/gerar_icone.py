"""Gera o icone do programa: as quatro formas da caixa num quadrado escuro.

Rodado pelo construir.ps1; nao precisa ser chamado na mao.
"""

import os
import sys

import cv2
import numpy as np

try:
    from PIL import Image
except ImportError:
    sys.exit("falta o Pillow: python -m pip install pillow")

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "icone.ico")

# cores em BGR, as mesmas da pagina
CIRCULO, QUADRADO, TRIANGULO, ESTRELA = (120, 120, 255), (120, 255, 120), (80, 200, 255), (255, 90, 210)


def estrela(cx, cy, re, ri):
    pontos = []
    for i in range(10):
        ang = -np.pi / 2 + i * np.pi / 5
        raio = re if i % 2 == 0 else ri
        pontos.append([cx + np.cos(ang) * raio, cy + np.sin(ang) * raio])
    return np.array(pontos, np.int32)


def desenhar(tamanho: int) -> np.ndarray:
    img = np.zeros((tamanho, tamanho, 4), np.uint8)
    t = tamanho
    # fundo arredondado
    raio = int(t * 0.18)
    cv2.rectangle(img, (raio, 0), (t - raio, t), (30, 25, 20, 255), -1)
    cv2.rectangle(img, (0, raio), (t, t - raio), (30, 25, 20, 255), -1)
    for cx, cy in ((raio, raio), (t - raio, raio), (raio, t - raio), (t - raio, t - raio)):
        cv2.circle(img, (cx, cy), raio, (30, 25, 20, 255), -1)

    # divisorias da caixa
    cv2.line(img, (t // 2, int(t * .1)), (t // 2, int(t * .9)), (70, 62, 55, 255), max(1, t // 32))
    cv2.line(img, (int(t * .1), t // 2), (int(t * .9), t // 2), (70, 62, 55, 255), max(1, t // 32))

    q = t // 4          # centro de cada quadrante
    r = int(t * 0.14)   # raio das formas
    cv2.circle(img, (q, q), r, (*CIRCULO, 255), -1)
    cv2.rectangle(img, (3 * q - r, q - r), (3 * q + r, q + r), (*QUADRADO, 255), -1)
    cv2.drawContours(img, [np.array([[q, 3 * q - r], [q - r, 3 * q + r], [q + r, 3 * q + r]])],
                     -1, (*TRIANGULO, 255), -1)
    cv2.drawContours(img, [estrela(3 * q, 3 * q, int(r * 1.15), int(r * 0.5))], -1, (*ESTRELA, 255), -1)
    return img


camadas = []
for tamanho in (16, 24, 32, 48, 64, 128, 256):
    bgra = desenhar(tamanho)
    rgba = cv2.cvtColor(bgra, cv2.COLOR_BGRA2RGBA)
    camadas.append(Image.fromarray(rgba))

camadas[-1].save(SAIDA, format="ICO", sizes=[(c.width, c.height) for c in camadas],
                 append_images=camadas[:-1])
print(f"icone gerado: {SAIDA}")
