"""Esteira simulada, para rodar o programa sem a placa.

Serve para desenvolver sem hardware e, mais importante, como plano B na
apresentacao: se a camera falhar na hora, `--demo` mostra o sistema inteiro
funcionando com pecas desenhadas.

Imita a interface da classe Camera (ponte.py), entao o resto do programa nao
sabe a diferenca.
"""

import random
import threading
import time

import cv2
import numpy as np

LARGURA, ALTURA = 320, 240
FUNDO = (238, 236, 232)     # BGR: papel branco meio quente
TINTA = (28, 28, 28)


def _estrela(cx, cy, re, ri):
    pontos = []
    for i in range(10):
        ang = -np.pi / 2 + i * np.pi / 5
        raio = re if i % 2 == 0 else ri
        pontos.append([cx + np.cos(ang) * raio, cy + np.sin(ang) * raio])
    return np.array(pontos, np.int32)


def _desenhar_peca(img, tipo, cx, cy, ang):
    """Desenha a peca girada de `ang` graus, como uma peca solta na esteira."""
    if tipo == "circulo":
        cv2.circle(img, (cx, cy), 27, TINTA, -1)
        return
    if tipo == "quadrado":
        pontos = cv2.boxPoints(((cx, cy), (52, 52), ang))
    elif tipo == "retangulo":
        pontos = cv2.boxPoints(((cx, cy), (70, 40), ang))
    elif tipo == "triangulo":
        base = np.array([[0, -32], [-34, 26], [34, 26]], np.float32)
        m = cv2.getRotationMatrix2D((0, 0), ang, 1.0)[:, :2]
        pontos = base @ m.T + (cx, cy)
    elif tipo == "estrela":
        base = _estrela(0, 0, 34, 14).astype(np.float32)
        m = cv2.getRotationMatrix2D((0, 0), ang, 1.0)[:, :2]
        pontos = base @ m.T + (cx, cy)
    else:
        return
    cv2.drawContours(img, [np.round(pontos).astype(np.int32)], -1, TINTA, -1)


class EsteiraSimulada:
    porta = "demo"

    def __init__(self, fps: float = 18.0, velocidade: float = 3.2):
        self.fps = fps
        self.velocidade = velocidade
        self.conectada = True
        self.quadros_lidos = 0
        self.quadros_descartados = 0
        self.ultimo_erro = ""
        self.sequencia = 0
        self._quadro = None
        self._trava = threading.Lock()
        self._rodando = False
        self._pecas: list[dict] = []
        self._proxima_em = 0.0

    # ------------------------------------------- mesma interface da Camera ---

    def iniciar(self) -> None:
        self._rodando = True
        threading.Thread(target=self._laco, daemon=True).start()

    def parar(self) -> None:
        self._rodando = False

    def esperar_conexao(self, segundos: float = 10.0) -> bool:
        limite = time.monotonic() + segundos
        while time.monotonic() < limite:
            if self._quadro is not None:
                return True
            time.sleep(0.05)
        return False

    def quadro(self):
        with self._trava:
            return None if self._quadro is None else self._quadro.copy()

    def quadro_novo(self, ultima_sequencia: int):
        with self._trava:
            if self._quadro is None or self.sequencia == ultima_sequencia:
                return ultima_sequencia, None
            return self.sequencia, self._quadro.copy()

    def comando(self, texto: str) -> None:
        pass    # nao ha placa para receber

    # ------------------------------------------------------------ esteira ---

    def _laco(self) -> None:
        intervalo = 1.0 / self.fps
        tipos = ["circulo", "quadrado", "triangulo", "estrela", "circulo",
                 "triangulo", "retangulo", "quadrado", "estrela"]
        indice = 0

        while self._rodando:
            agora = time.monotonic()

            # solta uma peca nova de tempos em tempos, pela borda esquerda
            if agora >= self._proxima_em:
                self._pecas.append({
                    "tipo": tipos[indice % len(tipos)],
                    "x": -45.0,
                    "y": random.randint(85, 155),
                    "ang": random.uniform(0, 360),
                    "giro": random.uniform(-0.6, 0.6),
                })
                indice += 1
                self._proxima_em = agora + random.uniform(2.4, 3.6)

            img = np.full((ALTURA, LARGURA, 3), FUNDO, np.uint8)
            # textura leve, para nao ficar um branco irreal
            ruido = np.random.randint(-6, 7, (ALTURA, LARGURA, 1), np.int16)
            img = np.clip(img.astype(np.int16) + ruido, 0, 255).astype(np.uint8)

            for p in self._pecas:
                p["x"] += self.velocidade
                p["ang"] += p["giro"]
                _desenhar_peca(img, p["tipo"], int(p["x"]), int(p["y"]), p["ang"])
            self._pecas = [p for p in self._pecas if p["x"] < LARGURA + 50]

            with self._trava:
                self._quadro = img
                self.sequencia += 1
            self.quadros_lidos += 1
            time.sleep(intervalo)
