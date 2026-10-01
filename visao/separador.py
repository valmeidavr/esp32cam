"""Manda para o ESP32 dos servos (COM5) em qual compartimento cada peca cai.

O ESP32-CAM so filma; este e outro ESP32, ligado em outra porta USB, que move
a cacamba. Cada peca que cruza a linha de despejo vira um numero:

    circulo = 1   quadrado = 2   triangulo = 3   estrela = 4

Enviar nunca pode travar o laco de visao: o comando entra numa fila e uma
thread propria cuida da serial — inclusive de reabrir a porta se o cabo sair.
"""

import queue
import threading
import time

import serial

PORTA_PADRAO = "COM5"
BAUD = 115200

COMANDOS = {
    "circulo":   "1",
    "quadrado":  "2",
    "triangulo": "3",
    "estrela":   "4",
}

ESPERA_BOOT = 2.0     # abrir a serial reinicia o ESP32; ele leva um tempo para acordar


class Separador:
    def __init__(self, porta: str = PORTA_PADRAO, baud: int = BAUD):
        self.porta = porta
        self.baud = baud
        self.conectado = False
        self.enviados = 0
        self.ultimo_erro = ""
        self._fila: queue.Queue[str] = queue.Queue(maxsize=32)
        self._rodando = False
        self._serial: serial.Serial | None = None

    def iniciar(self) -> None:
        self._rodando = True
        threading.Thread(target=self._supervisor, daemon=True).start()

    def parar(self) -> None:
        self._rodando = False

    def enviar(self, compartimento: str) -> bool:
        """Enfileira o comando do compartimento. False se ele nao tem servo."""
        comando = COMANDOS.get(compartimento)
        if comando is None:
            return False        # "outros": a peca nao tem compartimento
        try:
            self._fila.put_nowait(comando)
        except queue.Full:
            return False
        return True

    # ------------------------------------------------------------- serial ---

    def _supervisor(self) -> None:
        while self._rodando:
            try:
                self._abrir()
                self._servir()
            except (serial.SerialException, OSError) as erro:
                self.ultimo_erro = str(erro)
            finally:
                self._fechar()
            if self._rodando:
                time.sleep(2.0)

    def _abrir(self) -> None:
        self._serial = serial.Serial(self.porta, self.baud, timeout=0.2)
        time.sleep(ESPERA_BOOT)
        self._serial.reset_input_buffer()
        self.conectado = True
        self.ultimo_erro = ""

    def _fechar(self) -> None:
        self.conectado = False
        try:
            if self._serial and self._serial.is_open:
                self._serial.close()
        except Exception:
            pass
        self._serial = None

    def _servir(self) -> None:
        while self._rodando:
            try:
                comando = self._fila.get(timeout=0.2)
            except queue.Empty:
                self._serial.read(256)       # esvazia os "OK n" que o ESP32 devolve
                continue
            self._serial.write(comando.encode())
            self._serial.flush()
            self.enviados += 1
