"""Regras que separam peca de "resto da cena": cor, borda, area util, sanidade."""

import cv2
import numpy as np
import pytest

from detector import detectar, detectar_com_mascara, segmentar
from rastreador import Rastreador

from conftest import ALTURA, LARGURA, desenhar, quadro_vazio

AMARELO = (40, 220, 240)      # BGR: bloco de espuma amarelo, claro como o fundo


def _amarelo_sobre_cinza():
    """Amarelo sobre cinza-claro: quase nenhum contraste em cinza, muito em saturacao."""
    img = np.full((ALTURA, LARGURA, 3), 200, np.uint8)
    cv2.rectangle(img, (110, 70), (210, 170), AMARELO, -1)
    return img


@pytest.mark.parametrize("modo", ["cor", "ambos"])
def test_peca_colorida_clara_e_detectada_por_cor(modo):
    assert [f.nome for f in detectar(_amarelo_sobre_cinza(), modo=modo)] == ["quadrado"]


def test_forma_so_desenhada_no_papel_e_detectada_por_bordas():
    """Um circulo desenhado a lapis (traco cinza, sem preenchimento): nao e
    colorido nem escuro, entao o modo por cor nao ve nada; o por bordas ve."""
    img = quadro_vazio()
    cv2.circle(img, (160, 120), 40, (150, 150, 150), 3)
    assert [f.nome for f in detectar(img, modo="bordas")] == ["circulo"]
    assert detectar(img, modo="cor") == []
    # a caneta preta os dois veem
    img = quadro_vazio()
    cv2.circle(img, (160, 120), 40, (30, 30, 30), 3)
    assert [f.nome for f in detectar(img, modo="bordas")] == ["circulo"]
    assert [f.nome for f in detectar(img, modo="cor")] == ["circulo"]


@pytest.mark.parametrize("modo", ["bordas", "cor", "ambos"])
def test_peca_escura_e_detectada_em_todos_os_modos(cena, modo):
    assert [f.nome for f in detectar(cena([("circulo", 160, 120)]), modo=modo)] == ["circulo"]


def test_modo_padrao_e_bordas():
    from detector import MODO_PADRAO
    assert MODO_PADRAO == "bordas"


def test_fundo_com_gradiente_de_luz_nao_vira_peca():
    """Sombra suave na esteira (V entre 120 e 220) nao e peca."""
    img = np.zeros((ALTURA, LARGURA, 3), np.uint8)
    for x in range(LARGURA):
        img[:, x] = 120 + int(100 * x / LARGURA)
    assert detectar(img) == []


def test_encostado_na_borda_e_ignorado():
    img = quadro_vazio()
    desenhar(img, "quadrado", 20, 120, tamanho=30)          # sai pela esquerda
    desenhar(img, "circulo", 160, 120, tamanho=30)           # inteira
    assert [f.nome for f in detectar(img)] == ["circulo"]


def test_area_da_esteira_ignora_o_que_esta_fora():
    img = quadro_vazio()
    desenhar(img, "circulo", 60, 60, tamanho=22)             # fora da ROI
    desenhar(img, "triangulo", 200, 150, tamanho=26)         # dentro
    roi = (120, 90, 300, 230)
    formas = detectar(img, roi=roi)
    assert [f.nome for f in formas] == ["triangulo"]
    assert detectar(img) and len(detectar(img)) == 2         # sem ROI ve as duas


def test_linha_fina_nao_e_peca():
    """Uma borda de folha ou um risco: comprido, sem area. Nao pode virar forma."""
    img = quadro_vazio()
    cv2.line(img, (40, 40), (280, 200), (20, 20, 20), 3)
    assert detectar(img, area_minima=200) == []


def test_mancha_irregular_vira_poligono_nao_estrela():
    """Concava sem o padrao de estrela: nao pode ser promovida a estrela."""
    img = quadro_vazio()
    pts = np.array([[100, 60], [220, 70], [200, 120], [230, 190], [120, 180], [150, 120]], np.int32)
    cv2.fillPoly(img, [pts], (20, 20, 20))
    formas = detectar(img)
    assert formas and formas[0].nome == "poligono"


def test_mascara_respeita_limiares():
    img = _amarelo_sobre_cinza()
    assert segmentar(img, sat_min=90, escuro=70, modo="cor").sum() > 0
    assert segmentar(img, sat_min=250, escuro=0, modo="cor").sum() == 0   # nada e "colorido" o bastante


def test_detectar_com_mascara_devolve_os_dois():
    img = quadro_vazio()
    desenhar(img, "circulo", 160, 120)
    formas, mascara = detectar_com_mascara(img, modo="cor")
    assert len(formas) == 1 and mascara.shape == (ALTURA, LARGURA)
    assert mascara[120, 160] == 255 and mascara[10, 10] == 0
    # no modo por bordas a mascara e so o contorno: miolo vazio, borda cheia
    formas, mascara = detectar_com_mascara(img, modo="bordas")
    assert len(formas) == 1 and mascara[120, 160] == 0 and mascara.sum() > 0


# ------------------------------------------------------- regras de contagem ---

def _passar(r, tipo, y=120, tamanho=28):
    eventos = []
    for x in range(40, 290, 20):
        img = quadro_vazio()
        desenhar(img, tipo, x, y, tamanho=tamanho)
        eventos += r.atualizar(detectar(img))
    for _ in range(r.quadros_para_sumir + 1):
        eventos += r.atualizar([])
    return eventos


def test_poligono_nao_entra_na_conta():
    from detector import Forma
    r = Rastreador(largura=320)
    contorno = np.zeros((6, 1, 2), np.int32)
    eventos = []
    for x in range(100, 300, 25):
        eventos += r.atualizar([Forma("poligono", contorno, (x, 120), 900.0, 6, 0.5, 0.6)])
    assert eventos == []


def test_confianca_baixa_vai_para_outros():
    from detector import Forma
    r = Rastreador(largura=320, minimo_para_contar=2)
    contorno = np.zeros((4, 1, 2), np.int32)
    votos = ["quadrado", "circulo", "quadrado", "circulo", "triangulo", "quadrado"]   # 50%
    eventos = []
    for i, nome in enumerate(votos):
        eventos += r.atualizar([Forma(nome, contorno, (100 + i * 25, 120), 900.0, 4, 0.8, 1.0)])
    assert len(eventos) == 1
    assert eventos[0].compartimento == "outros"


def test_duas_pecas_lado_a_lado_contam_as_duas():
    """Uma em cima e outra embaixo, andando juntas: cada uma no seu compartimento."""
    r = Rastreador(largura=320)
    eventos = []
    for x in range(40, 290, 20):
        img = quadro_vazio()
        desenhar(img, "quadrado", x, 65, tamanho=26)
        desenhar(img, "circulo", x + 15, 175, tamanho=26)
        eventos += r.atualizar(detectar(img))
    assert sorted(e.compartimento for e in eventos) == ["circulo", "quadrado"]
    assert len({e.id for e in eventos}) == 2
