"""Cada peca e contada uma vez, no compartimento certo."""

from detector import detectar
from rastreador import Rastreador

from conftest import LARGURA, desenhar, quadro_vazio


def passar_peca(r, tipo, y=120, passo=24, ang=0.0):
    """Faz uma peca atravessar a cena da esquerda para a direita."""
    eventos = []
    for x in range(-20, LARGURA + 40, passo):
        img = quadro_vazio()
        desenhar(img, tipo, x, y, ang)
        eventos += r.atualizar(detectar(img))
    for _ in range(r.quadros_para_sumir + 1):          # cena vazia: solta a peca
        eventos += r.atualizar([])
    return eventos


def test_conta_uma_vez_por_peca():
    r = Rastreador(largura=LARGURA)
    fila = ["circulo", "quadrado", "triangulo", "estrela", "circulo"]
    eventos = [e for tipo in fila for e in passar_peca(r, tipo)]
    assert [e.forma for e in eventos] == fila
    assert [e.compartimento for e in eventos] == fila


def test_ids_sao_sequenciais_e_unicos():
    r = Rastreador(largura=LARGURA)
    eventos = passar_peca(r, "circulo") + passar_peca(r, "quadrado")
    assert [e.id for e in eventos] == [1, 2]


def test_retangulo_vai_para_outros():
    r = Rastreador(largura=LARGURA)
    (e,) = passar_peca(r, "retangulo")
    assert e.forma == "retangulo" and e.compartimento == "outros"


def test_nao_conta_peca_que_nao_cruza_a_linha():
    r = Rastreador(largura=LARGURA)
    r.definir_linha(300)
    eventos = []
    for x in range(40, 200, 20):                       # para antes da linha
        img = quadro_vazio()
        desenhar(img, "circulo", x, 120)
        eventos += r.atualizar(detectar(img))
    for _ in range(r.quadros_para_sumir + 1):
        eventos += r.atualizar([])
    assert eventos == []


def test_modo_saida_conta_ao_sumir():
    r = Rastreador(largura=LARGURA)
    r.definir_modo("saida")
    r.definir_linha(310)                               # linha fora do caminho
    eventos = []
    for x in range(60, 160, 20):
        img = quadro_vazio()
        desenhar(img, "triangulo", x, 120)
        eventos += r.atualizar(detectar(img))
    assert eventos == []                               # ainda na cena
    for _ in range(r.quadros_para_sumir + 1):
        eventos += r.atualizar([])
    assert [e.forma for e in eventos] == ["triangulo"]


def test_voto_da_maioria_vence_quadro_errado():
    """Um quadro borrado que vira 'poligono' nao pode mudar a resposta."""
    from detector import Forma
    import numpy as np

    r = Rastreador(largura=LARGURA, minimo_para_contar=3)
    contorno = np.array([[[0, 0]], [[10, 0]], [[10, 10]], [[0, 10]]], np.int32)

    def deteccao(nome, x):
        return Forma(nome, contorno, (x, 120), 900.0, 4, 0.8, 1.0)

    votos = ["circulo", "circulo", "poligono", "circulo", "circulo", "circulo"]
    eventos = []
    for i, nome in enumerate(votos):
        eventos += r.atualizar([deteccao(nome, 100 + i * 25)])   # cruza x=192 no 4o
    assert [e.forma for e in eventos] == ["circulo"]
    assert eventos[0].confianca < 1.0


def test_duas_pecas_ao_mesmo_tempo():
    r = Rastreador(largura=LARGURA)
    eventos = []
    for x in range(-20, LARGURA + 40, 24):
        img = quadro_vazio()
        desenhar(img, "circulo", x, 70)
        desenhar(img, "estrela", x - 10, 175)
        eventos += r.atualizar(detectar(img))
    assert sorted(e.forma for e in eventos) == ["circulo", "estrela"]


def test_zerar_esquece_as_pecas():
    r = Rastreador(largura=LARGURA)
    img = quadro_vazio()
    desenhar(img, "circulo", 100, 120)
    r.atualizar(detectar(img))
    assert len(r.pecas) == 1
    r.zerar()
    assert r.pecas == []


def test_linha_fica_dentro_da_imagem():
    r = Rastreador(largura=LARGURA)
    r.definir_linha(-50)
    assert r.linha == 10
    r.definir_linha(9999)
    assert r.linha == LARGURA - 10
