"""O detector reconhece cada forma, inclusive girada, e ignora ruido."""

import numpy as np
import pytest

from detector import detectar

from conftest import desenhar, quadro_vazio

TODAS = ["circulo", "quadrado", "retangulo", "triangulo", "estrela", "pentagono", "hexagono"]


@pytest.mark.parametrize("tipo", TODAS)
def test_reconhece_cada_forma(cena, tipo):
    formas = detectar(cena([(tipo, 160, 120)]))
    assert [f.nome for f in formas] == [tipo]


@pytest.mark.parametrize("tipo", ["circulo", "quadrado", "triangulo", "estrela"])
@pytest.mark.parametrize("ang", [0, 17, 45, 90, 133])
def test_reconhece_girada(cena, tipo, ang):
    """A peca cai na esteira em qualquer angulo; a forma nao pode mudar."""
    formas = detectar(cena([(tipo, 160, 120)], ang=ang))
    assert [f.nome for f in formas] == [tipo], f"{tipo} a {ang} graus"


def test_varias_pecas_no_mesmo_quadro(cena):
    formas = detectar(cena([
        ("circulo", 55, 60), ("quadrado", 160, 60), ("triangulo", 265, 60),
        ("estrela", 80, 175), ("hexagono", 230, 175),
    ]))
    assert sorted(f.nome for f in formas) == ["circulo", "estrela", "hexagono", "quadrado", "triangulo"]


def test_ordena_da_maior_para_a_menor():
    img = quadro_vazio()
    desenhar(img, "circulo", 80, 120, tamanho=40)
    desenhar(img, "quadrado", 230, 120, tamanho=18)
    formas = detectar(img)
    assert [f.nome for f in formas] == ["circulo", "quadrado"]
    assert formas[0].area > formas[1].area


def test_ignora_ruido_pequeno():
    img = quadro_vazio()
    desenhar(img, "quadrado", 160, 120, tamanho=6)     # ~150 px de area
    assert detectar(img, area_minima=700) == []
    assert len(detectar(img, area_minima=50)) == 1


def test_ignora_moldura_da_imagem_inteira():
    """Um contorno que envolve o quadro todo e a borda, nao uma peca."""
    img = np.full((240, 320, 3), 20, np.uint8)
    img[4:-4, 4:-4] = 240
    assert detectar(img) == []


def test_quadro_vazio_nao_detecta_nada():
    assert detectar(quadro_vazio()) == []


def test_centro_da_forma(cena):
    (f,) = detectar(cena([("circulo", 100, 150)]))
    assert abs(f.centro[0] - 100) <= 2 and abs(f.centro[1] - 150) <= 2


def test_estrela_tem_solidez_baixa_e_circulo_alta(cena):
    (estrela,) = detectar(cena([("estrela", 160, 120)]))
    (circulo,) = detectar(cena([("circulo", 160, 120)]))
    assert estrela.solidez < 0.72 < circulo.solidez
    assert circulo.circularidade > 0.8
