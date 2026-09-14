"""Acompanha cada peca enquanto ela atravessa a esteira.

Sem isso a contagem nao presta: a camera ve a mesma peca em 15 quadros
seguidos e, contando quadro a quadro, um unico circulo viraria 15 circulos.
Aqui cada peca ganha um numero, e ela so entra na conta uma vez — quando
cruza a linha de despejo, ja no fim da esteira.

Acompanhar tambem deixa a classificacao mais firme: em vez de confiar no que
o detector disse num quadro so, vale o que ele disse na maioria dos quadros
em que aquela peca apareceu.
"""

import time
from collections import Counter
from dataclasses import dataclass, field

from detector import Forma

# Para onde cada forma vai na caixa. O que nao tem compartimento proprio cai
# em "outros" — e mais honesto do que empurrar um retangulo para dentro do
# compartimento do quadrado.
COMPARTIMENTOS = {
    "circulo":   "circulo",
    "quadrado":  "quadrado",
    "triangulo": "triangulo",
    "estrela":   "estrela",
}
COMPARTIMENTO_PADRAO = "outros"

# Abaixo disto os quadros discordaram demais sobre a forma: a peca vai para
# "outros" em vez de cair num compartimento errado.
CONFIANCA_MINIMA = 0.60


@dataclass(eq=False)     # guarda um contorno numpy: ver o comentario em Forma
class Peca:
    id: int
    centro: tuple[int, int]
    area: float
    contorno: object = None      # ultimo contorno visto, so para desenhar
    votos: Counter = field(default_factory=Counter)
    quadros_vista: int = 0
    quadros_sumida: int = 0
    contada: bool = False
    lado: int = 0            # de que lado da linha de despejo ela estava

    @property
    def nome(self) -> str:
        """A forma mais votada nos quadros em que esta peca apareceu."""
        return self.votos.most_common(1)[0][0] if self.votos else "poligono"

    @property
    def confianca(self) -> float:
        """Fracao dos quadros que concordaram com a forma vencedora."""
        if not self.votos:
            return 0.0
        return self.votos.most_common(1)[0][1] / sum(self.votos.values())

    @property
    def compartimento(self) -> str:
        if self.confianca < CONFIANCA_MINIMA:
            return COMPARTIMENTO_PADRAO
        return COMPARTIMENTOS.get(self.nome, COMPARTIMENTO_PADRAO)

    @property
    def e_peca(self) -> bool:
        """'poligono' e o que o detector nao conseguiu nomear — uma mancha,
        uma sombra, um pedaco de outra coisa. Isso nao entra na conta."""
        return self.nome != "poligono"


@dataclass
class Despejo:
    """Uma peca terminou o trajeto e caiu num compartimento."""
    id: int
    forma: str
    compartimento: str
    confianca: float
    instante: float


class Rastreador:
    """Casa as deteccoes de cada quadro com as pecas que ja estavam na cena.

    O criterio e a distancia entre os centros: como a esteira anda devagar
    perto da taxa de quadros da camera, a peca mal sai do lugar entre um
    quadro e o seguinte, e o vizinho mais proximo e ela mesma.
    """

    def __init__(self, largura: int = 320,
                 distancia_maxima: int = 70,
                 quadros_para_sumir: int = 8,
                 minimo_para_contar: int = 3):
        self.largura = largura
        self.distancia_maxima = distancia_maxima
        self.quadros_para_sumir = quadros_para_sumir
        self.minimo_para_contar = minimo_para_contar

        self.linha = int(largura * 0.60)   # posicao x da linha de despejo
        self.modo = "linha"                # "linha" ou "saida"

        self._pecas: dict[int, Peca] = {}
        self._proximo_id = 1

    # ------------------------------------------------------------ ajustes ---

    def definir_linha(self, x: int) -> None:
        self.linha = max(10, min(self.largura - 10, int(x)))

    def definir_modo(self, modo: str) -> None:
        if modo in ("linha", "saida"):
            self.modo = modo

    def zerar(self) -> None:
        self._pecas.clear()

    # ------------------------------------------------------------- pecas ---

    @property
    def pecas(self) -> list[Peca]:
        """Pecas visiveis agora (as que sumiram ficam de fora)."""
        return [p for p in self._pecas.values() if p.quadros_sumida == 0]

    def _lado_da_linha(self, x: int) -> int:
        return 1 if x >= self.linha else -1

    def _casar(self, formas: list[Forma]) -> dict[int, Forma]:
        """Liga cada peca conhecida a deteccao mais proxima deste quadro.

        Todos os pares (peca, deteccao) sao ordenados pela distancia e
        atribuidos do mais perto para o mais longe. Com duas pecas lado a
        lado, isso impede que a primeira da lista "roube" a deteccao que na
        verdade pertence a segunda.
        """
        pares = []
        for id_peca, peca in self._pecas.items():
            for indice, forma in enumerate(formas):
                d2 = ((forma.centro[0] - peca.centro[0]) ** 2
                      + (forma.centro[1] - peca.centro[1]) ** 2)
                if d2 <= self.distancia_maxima ** 2:
                    pares.append((d2, id_peca, indice))
        pares.sort()

        casadas: dict[int, Forma] = {}
        usadas: set[int] = set()
        for _, id_peca, indice in pares:
            if id_peca in casadas or indice in usadas:
                continue
            casadas[id_peca] = formas[indice]
            usadas.add(indice)
        return casadas

    # ----------------------------------------------------------- ciclo ---

    def atualizar(self, formas: list[Forma]) -> list[Despejo]:
        """Consome as deteccoes de um quadro e devolve os despejos ocorridos."""
        despejos: list[Despejo] = []
        casadas = self._casar(formas)
        usadas = set(id(f) for f in casadas.values())   # por identidade, nunca por ==

        # 1. pecas que continuam na cena
        for id_peca, forma in casadas.items():
            peca = self._pecas[id_peca]
            anterior = peca.lado

            peca.centro = forma.centro
            peca.area = forma.area
            peca.contorno = forma.contorno
            peca.votos[forma.nome] += 1
            peca.quadros_vista += 1
            peca.quadros_sumida = 0
            peca.lado = self._lado_da_linha(forma.centro[0])

            if (self.modo == "linha" and not peca.contada and peca.e_peca
                    and anterior != 0 and peca.lado != anterior
                    and peca.quadros_vista >= self.minimo_para_contar):
                peca.contada = True
                despejos.append(self._despejar(peca))

        # 2. pecas que nao apareceram neste quadro
        for id_peca, peca in list(self._pecas.items()):
            if id_peca in casadas:
                continue
            peca.quadros_sumida += 1
            if peca.quadros_sumida < self.quadros_para_sumir:
                continue

            # Sumiu de vez. No modo "saida" e aqui que ela e contada.
            if (self.modo == "saida" and not peca.contada and peca.e_peca
                    and peca.quadros_vista >= self.minimo_para_contar):
                peca.contada = True
                despejos.append(self._despejar(peca))
            del self._pecas[id_peca]

        # 3. deteccoes que nao eram de ninguem: pecas novas
        for forma in formas:
            if id(forma) in usadas:
                continue
            peca = Peca(id=self._proximo_id, centro=forma.centro, area=forma.area,
                        contorno=forma.contorno)
            peca.votos[forma.nome] += 1
            peca.quadros_vista = 1
            peca.lado = self._lado_da_linha(forma.centro[0])
            self._pecas[self._proximo_id] = peca
            self._proximo_id += 1

        return despejos

    def _despejar(self, peca: Peca) -> Despejo:
        return Despejo(
            id=peca.id,
            forma=peca.nome,
            compartimento=peca.compartimento,
            confianca=round(peca.confianca, 2),
            instante=time.time(),
        )
