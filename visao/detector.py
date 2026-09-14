"""Deteccao e classificacao de formas geometricas.

Ha dois jeitos de separar "peca" de "fundo", escolhidos pelo modo:

  bordas  (padrao) detector de bordas (Canny). Enxerga qualquer coisa com
          contorno nitido — inclusive uma forma so desenhada ou recortada em
          papel, sem cor nem preenchimento. E o que funciona melhor com as
          pecas usadas neste projeto.
  cor     segmenta o que e colorido ou escuro sobre a esteira clara. Rende
          regioes cheias e aguenta imagem borrada, mas nao ve peca clara e
          sem cor.
  ambos   uniao dos dois.

A classificacao sai da geometria do contorno (vertices, circularidade,
solidez); nao ha rede neural, roda offline e nao erra de um jeito
imprevisivel.
"""

from dataclasses import dataclass

import cv2
import numpy as np

# Limiares padrao. Podem ser ajustados na pagina, com a visao da mascara.
MODO_PADRAO = "bordas"
MODOS = ("bordas", "cor", "ambos")
SATURACAO_MINIMA = 90     # abaixo disso e "sem cor" (papel, esteira, cinza)
ESCURO_MAXIMO = 70        # valor (brilho) abaixo disso e "escuro" (peca preta)
AREA_MAXIMA = 0.70        # fracao da area util; maior que isso e o fundo, nao uma peca
EXTENSAO_MINIMA = 0.30    # area / caixa envolvente; linhas e riscos ficam abaixo


# eq=False: com o __eq__ que o dataclass gera, comparar duas formas compara os
# contornos (arrays numpy de tamanhos diferentes) e estoura um ValueError —
# foi isso que congelava o video. Aqui igualdade e identidade, como deve ser.
@dataclass(eq=False)
class Forma:
    nome: str
    contorno: np.ndarray
    centro: tuple[int, int]
    area: float
    vertices: int
    circularidade: float
    solidez: float = 1.0

    @property
    def cor(self) -> tuple[int, int, int]:
        """Cor BGR do desenho, uma por tipo de forma."""
        return CORES.get(self.nome, (200, 200, 200))


CORES = {
    "estrela":   (255, 90, 210),    # roxo
    "triangulo": (80, 200, 255),    # amarelo-alaranjado
    "quadrado":  (120, 255, 120),   # verde
    "retangulo": (255, 190, 90),    # azul claro
    "pentagono": (180, 180, 90),    # verde-agua
    "hexagono":  (90, 160, 255),    # laranja
    "circulo":   (120, 120, 255),   # vermelho claro
    "poligono":  (200, 200, 200),   # cinza
}


# ------------------------------------------------------------- segmentacao ---

def _mascara_por_bordas(quadro: np.ndarray) -> np.ndarray:
    """Canny sobre a imagem em cinza; o dilate costura as bordas que sairam
    picadas e o erode devolve a espessura. E o metodo original do projeto."""
    cinza = cv2.GaussianBlur(cv2.cvtColor(quadro, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    bordas = cv2.Canny(cinza, 50, 150)
    bordas = cv2.dilate(bordas, np.ones((3, 3), np.uint8), iterations=2)
    return cv2.erode(bordas, np.ones((3, 3), np.uint8), iterations=1)


def _mascara_por_cor(quadro: np.ndarray, sat_min: int, escuro: int) -> np.ndarray:
    """Colorido OU escuro, com buracos pequenos fechados e pontinhos removidos."""
    hsv = cv2.cvtColor(cv2.GaussianBlur(quadro, (5, 5), 0), cv2.COLOR_BGR2HSV)
    s, v = hsv[..., 1], hsv[..., 2]
    mascara = ((s >= sat_min) | (v <= escuro)).astype(np.uint8) * 255
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    return cv2.morphologyEx(mascara, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))


def segmentar(quadro: np.ndarray, sat_min: int = SATURACAO_MINIMA,
              escuro: int = ESCURO_MAXIMO, roi=None, modo: str = MODO_PADRAO) -> np.ndarray:
    """Mascara 0/255 do que parece peca, conforme o modo, dentro da ROI."""
    if modo == "cor":
        mascara = _mascara_por_cor(quadro, sat_min, escuro)
    elif modo == "ambos":
        mascara = cv2.bitwise_or(_mascara_por_bordas(quadro), _mascara_por_cor(quadro, sat_min, escuro))
    else:
        mascara = _mascara_por_bordas(quadro)

    if roi is not None:
        x1, y1, x2, y2 = roi
        recorte = np.zeros_like(mascara)
        recorte[y1:y2, x1:x2] = mascara[y1:y2, x1:x2]
        mascara = recorte
    return mascara


# ----------------------------------------------------------- classificacao ---

def _classificar(contorno: np.ndarray, area: float):
    """Devolve (nome, vertices, circularidade, solidez), ou None se o contorno
    nem parece uma peca (linha, risco, mancha sem forma)."""
    perimetro = cv2.arcLength(contorno, closed=True)
    if perimetro == 0:
        return None

    x, y, w, h = cv2.boundingRect(contorno)
    extensao = area / float(w * h) if w * h else 0.0
    if extensao < EXTENSAO_MINIMA:
        return None            # uma linha ou um risco, nao uma peca

    envoltoria = cv2.convexHull(contorno)
    area_envoltoria = cv2.contourArea(envoltoria)
    solidez = area / area_envoltoria if area_envoltoria > 0 else 0.0
    # 1.0 = circulo perfeito. Um quadrado da ~0.785, um triangulo ~0.60.
    circularidade = 4 * np.pi * area / (perimetro * perimetro)

    # ---- concavas: so a estrela e aceita ---------------------------------
    if solidez < 0.72:
        # Estrela de cinco pontas: solidez em torno de 0.5 (os vaos entre as
        # pontas nao contam), ~10 vertices com aproximacao fina, e a
        # envoltoria convexa e um pentagono. Os tres juntos separam a estrela
        # de uma mancha qualquer com reentrancias.
        pontas = len(cv2.approxPolyDP(contorno, 0.02 * perimetro, closed=True))
        lados_envoltoria = len(cv2.approxPolyDP(
            envoltoria, 0.04 * cv2.arcLength(envoltoria, True), closed=True))
        if 0.38 <= solidez <= 0.72 and 8 <= pontas <= 12 and 5 <= lados_envoltoria <= 6:
            return "estrela", pontas, circularidade, solidez
        return "poligono", pontas, circularidade, solidez

    # ---- convexas -----------------------------------------------------------
    if solidez < 0.85:
        return "poligono", 0, circularidade, solidez   # cheia demais para estrela, furada demais para forma

    # 4% do perimetro tolera bem o serrilhado de uma imagem 320x240 sem
    # arredondar os cantos de um triangulo de verdade.
    vertices = len(cv2.approxPolyDP(contorno, 0.04 * perimetro, closed=True))

    if vertices == 3:
        return "triangulo", vertices, circularidade, solidez

    if vertices == 4:
        # Quadrado ou retangulo: o minAreaRect ignora a rotacao, entao a peca
        # continua sendo reconhecida se estiver torta na esteira.
        (_, _), (largura, altura), _ = cv2.minAreaRect(contorno)
        if min(largura, altura) == 0:
            return "retangulo", vertices, circularidade, solidez
        proporcao = max(largura, altura) / min(largura, altura)
        return ("quadrado" if proporcao <= 1.18 else "retangulo"), vertices, circularidade, solidez

    if vertices == 5:
        return "pentagono", vertices, circularidade, solidez

    if vertices == 6:
        # Antes da circularidade: um hexagono regular chega a 0.91, ou seja,
        # e tao "redondo" quanto muitos circulos. Quem separa os dois aqui e
        # a contagem de vertices, nao o preenchimento.
        return "hexagono", vertices, circularidade, solidez

    # Passando de seis vertices a aproximacao ja nao diz muito — um circulo
    # vira um poligono de 8, 10, 12 lados conforme o serrilhado. Ai sim vale
    # o quanto o contorno preenche um circulo de mesmo perimetro.
    if circularidade >= 0.80:
        return "circulo", vertices, circularidade, solidez

    return "poligono", vertices, circularidade, solidez


# ---------------------------------------------------------------- deteccao ---

def detectar_com_mascara(quadro: np.ndarray, area_minima: int = 700,
                         sat_min: int = SATURACAO_MINIMA, escuro: int = ESCURO_MAXIMO,
                         roi=None, modo: str = MODO_PADRAO) -> tuple[list[Forma], np.ndarray]:
    """Devolve (formas da maior para a menor, mascara usada)."""
    altura, largura = quadro.shape[:2]
    if roi is None:
        x1, y1, x2, y2 = 0, 0, largura, altura
    else:
        x1, y1, x2, y2 = roi

    mascara = segmentar(quadro, sat_min, escuro, roi, modo)
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    area_util = max(1, (x2 - x1) * (y2 - y1))
    formas: list[Forma] = []

    for contorno in contornos:
        area = cv2.contourArea(contorno)
        if area < area_minima or area > AREA_MAXIMA * area_util:
            continue

        # Encostado na borda da area util: e uma peca entrando/saindo ou um
        # objeto de fora (mao, bancada). De um jeito ou de outro, nao da para
        # classificar este quadro; o rastreador vota nos quadros seguintes.
        bx, by, bw, bh = cv2.boundingRect(contorno)
        if bx <= x1 or by <= y1 or bx + bw >= x2 or by + bh >= y2:
            continue

        resultado = _classificar(contorno, area)
        if resultado is None:
            continue

        momentos = cv2.moments(contorno)
        if momentos["m00"] == 0:
            continue
        centro = (int(momentos["m10"] / momentos["m00"]),
                  int(momentos["m01"] / momentos["m00"]))

        nome, vertices, circularidade, solidez = resultado
        formas.append(Forma(nome, contorno, centro, area, vertices, circularidade, solidez))

    formas.sort(key=lambda f: f.area, reverse=True)
    return formas, mascara


def detectar(quadro: np.ndarray, area_minima: int = 700, **opcoes) -> list[Forma]:
    """Devolve as formas encontradas no quadro, da maior para a menor."""
    return detectar_com_mascara(quadro, area_minima, **opcoes)[0]


def desenhar(quadro: np.ndarray, formas: list[Forma]) -> np.ndarray:
    """Marca cada forma encontrada sobre uma copia do quadro."""
    saida = quadro.copy()

    for forma in formas:
        cv2.drawContours(saida, [forma.contorno], -1, forma.cor, 2)

        texto = forma.nome.upper()
        (largura_txt, altura_txt), _ = cv2.getTextSize(
            texto, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
        )
        x = forma.centro[0] - largura_txt // 2
        y = forma.centro[1] + altura_txt // 2

        # Tarja atras do texto: sem ela o rotulo some sobre fundo claro.
        cv2.rectangle(saida, (x - 4, y - altura_txt - 4), (x + largura_txt + 4, y + 4),
                      (0, 0, 0), cv2.FILLED)
        cv2.putText(saida, texto, (x, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, forma.cor, 1, cv2.LINE_AA)

    return saida
