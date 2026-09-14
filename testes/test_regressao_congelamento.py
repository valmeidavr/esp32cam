"""Regressao do bug que congelava o video.

Duas pecas no mesmo quadro, com contornos de tamanhos diferentes, em ordem
tal que a deteccao casada NAO e a primeira da lista. O rastreador antigo
fazia `lista.remove(forma)`, o dataclass comparava os contornos numpy com ==
e estourava ValueError, matando a thread de visao.
"""

import numpy as np
import pytest

from detector import Forma, detectar
from rastreador import Rastreador

from conftest import desenhar, quadro_vazio


def forma(nome, x, y, n_pontos):
    contorno = np.zeros((n_pontos, 1, 2), np.int32)
    return Forma(nome, contorno, (x, y), 900.0, 4, 0.8, 1.0)


def test_casar_nao_compara_contornos():
    r = Rastreador(largura=320)
    # quadro 1: a peca A e criada primeiro (id 1), depois B
    r.atualizar([forma("circulo", 60, 100, 54), forma("quadrado", 200, 100, 97)])
    # quadro 2: a lista chega invertida; ao casar a peca 1 (A) o vizinho mais
    # proximo e o segundo elemento, e o remove antigo comparava com o primeiro
    despejos = r.atualizar([forma("quadrado", 202, 100, 97), forma("circulo", 62, 100, 54)])
    assert despejos == []
    assert sorted(p.nome for p in r.pecas) == ["circulo", "quadrado"]


def test_formas_comparam_por_identidade():
    a = forma("circulo", 0, 0, 10)
    b = forma("circulo", 0, 0, 20)
    assert a != b and a == a
    assert [a, b].index(b) == 1        # nao levanta ValueError


def test_varias_pecas_reais_em_ordens_diferentes(cena):
    """Com pecas de tamanhos distintos a ordenacao por area muda a ordem da
    lista entre quadros; o rastreador tem de aguentar qualquer ordem."""
    r = Rastreador(largura=320)
    for x in range(60, 230, 15):                       # todas dentro da imagem
        img = quadro_vazio()
        desenhar(img, "circulo", x, 60, tamanho=30)
        desenhar(img, "estrela", 300 - x, 180, tamanho=22)
        desenhar(img, "triangulo", x + 40, 120, tamanho=16)
        r.atualizar(detectar(img, area_minima=200))    # nao pode levantar
    assert len(r.pecas) == 3
