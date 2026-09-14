"""Classificacao de formas geometricas por analise de contorno.

Nao usa rede neural: o formato sai da propria geometria do contorno, o que e
mais rapido, roda offline e nao erra de um jeito imprevisivel.
"""

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
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


def _classificar(contorno: np.ndarray, area: float) -> tuple[str, int, float, float]:
    perimetro = cv2.arcLength(contorno, closed=True)
    if perimetro == 0:
        return "poligono", 0, 0.0, 1.0

    # 4% do perimetro tolera bem o serrilhado de uma imagem 320x240 sem
    # arredondar os cantos de um triangulo de verdade.
    aprox = cv2.approxPolyDP(contorno, 0.04 * perimetro, closed=True)
    vertices = len(aprox)

    # 1.0 = circulo perfeito. Um quadrado da ~0.785, um triangulo ~0.60.
    circularidade = 4 * np.pi * area / (perimetro * perimetro)

    # Solidez = area / area do menor poligono convexo em volta. Formas cheias
    # ficam perto de 1.0; uma estrela de cinco pontas fica em torno de 0.5,
    # porque os vaos entre as pontas nao contam como area.
    envoltoria = cv2.convexHull(contorno)
    area_envoltoria = cv2.contourArea(envoltoria)
    solidez = area / area_envoltoria if area_envoltoria > 0 else 1.0

    if solidez < 0.72:
        # Forma concava. Aqui a aproximacao grossa de 4% comeria as pontas, e
        # a estrela viraria um pentagono — por isso o epsilon menor.
        pontas = len(cv2.approxPolyDP(contorno, 0.02 * perimetro, closed=True))
        if 8 <= pontas <= 12:
            return "estrela", pontas, circularidade, solidez
        return "poligono", pontas, circularidade, solidez

    if vertices == 3:
        return "triangulo", vertices, circularidade, solidez

    if vertices == 4:
        # Quadrado ou retangulo: o minAreaRect ignora a rotacao, entao a peca
        # continua sendo reconhecida se estiver torta na mesa.
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


def detectar(quadro: np.ndarray, area_minima: int = 700) -> list[Forma]:
    """Devolve as formas encontradas no quadro, da maior para a menor."""
    cinza = cv2.cvtColor(quadro, cv2.COLOR_BGR2GRAY)
    cinza = cv2.GaussianBlur(cinza, (5, 5), 0)

    # Canny se vira melhor que threshold fixo com a iluminacao irregular de
    # uma webcam caseira; o dilate depois costura as bordas que sairam picadas.
    bordas = cv2.Canny(cinza, 50, 150)
    bordas = cv2.dilate(bordas, np.ones((3, 3), np.uint8), iterations=2)
    bordas = cv2.erode(bordas, np.ones((3, 3), np.uint8), iterations=1)

    contornos, _ = cv2.findContours(bordas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    formas: list[Forma] = []
    altura, largura = quadro.shape[:2]
    area_do_quadro = altura * largura

    for contorno in contornos:
        area = cv2.contourArea(contorno)

        # Descarta ruido, e tambem a moldura inteira quando o Canny fecha um
        # contorno em volta da imagem toda.
        if area < area_minima or area > 0.90 * area_do_quadro:
            continue

        momentos = cv2.moments(contorno)
        if momentos["m00"] == 0:
            continue
        centro = (int(momentos["m10"] / momentos["m00"]),
                  int(momentos["m01"] / momentos["m00"]))

        nome, vertices, circularidade, solidez = _classificar(contorno, area)
        formas.append(
            Forma(nome, contorno, centro, area, vertices, circularidade, solidez)
        )

    formas.sort(key=lambda f: f.area, reverse=True)
    return formas


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
