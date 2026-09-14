"""Configuracao comum dos testes.

Coloca visao/ no caminho de importacao e oferece um "desenhista" de pecas
sinteticas: fundo claro, peca escura — o mesmo cenario da esteira real.
"""

import os
import sys

import cv2
import numpy as np
import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "visao"))

LARGURA, ALTURA = 320, 240
FUNDO = (240, 240, 240)
TINTA = (20, 20, 20)


def estrela(cx, cy, re, ri, pontas=5):
    pts = []
    for i in range(pontas * 2):
        ang = -np.pi / 2 + i * np.pi / pontas
        raio = re if i % 2 == 0 else ri
        pts.append([cx + np.cos(ang) * raio, cy + np.sin(ang) * raio])
    return np.array(pts, np.int32)


def poligono_regular(cx, cy, raio, lados):
    angs = np.linspace(0, 2 * np.pi, lados + 1)[:-1] - np.pi / 2
    return np.array([[cx + np.cos(a) * raio, cy + np.sin(a) * raio] for a in angs], np.int32)


def quadro_vazio():
    return np.full((ALTURA, LARGURA, 3), FUNDO, np.uint8)


def desenhar(img, tipo, cx, cy, ang=0.0, tamanho=30):
    """Desenha uma peca do `tipo` centrada em (cx, cy), girada `ang` graus."""
    r = tamanho
    if tipo == "circulo":
        cv2.circle(img, (cx, cy), r, TINTA, -1)
        return img
    if tipo == "quadrado":
        base = cv2.boxPoints(((0, 0), (2 * r, 2 * r), 0))
    elif tipo == "retangulo":
        base = cv2.boxPoints(((0, 0), (2.4 * r, 1.3 * r), 0))
    elif tipo == "triangulo":
        base = np.array([[0, -r], [-r * 1.1, r * 0.8], [r * 1.1, r * 0.8]], np.float32)
    elif tipo == "estrela":
        base = estrela(0, 0, r * 1.15, r * 0.48).astype(np.float32)
    elif tipo == "pentagono":
        base = poligono_regular(0, 0, r * 1.1, 5).astype(np.float32)
    elif tipo == "hexagono":
        base = poligono_regular(0, 0, r * 1.1, 6).astype(np.float32)
    else:
        raise ValueError(tipo)

    m = cv2.getRotationMatrix2D((0, 0), ang, 1.0)[:, :2]
    pts = np.round(base @ m.T + (cx, cy)).astype(np.int32)
    cv2.drawContours(img, [pts], -1, TINTA, -1)
    return img


@pytest.fixture
def cena():
    """Fabrica de quadros: cena([("circulo", 60, 60), ("estrela", 200, 150)])."""
    def _fazer(pecas, ang=0.0):
        img = quadro_vazio()
        for tipo, cx, cy in pecas:
            desenhar(img, tipo, cx, cy, ang)
        return img
    return _fazer
