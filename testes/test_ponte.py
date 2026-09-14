"""A leitura da serial decodifica os quadros e sobrevive a lixo no meio."""

import struct
import time

import cv2
import numpy as np
import pytest

import ponte
from ponte import MARCA, Camera


def jpeg_de_teste(valor: int) -> bytes:
    img = np.full((24, 32, 3), valor, np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


def quadro_serial(jpeg: bytes) -> bytes:
    return MARCA + struct.pack("<I", len(jpeg)) + jpeg


class SerialFalsa:
    """Substitui serial.Serial: entrega os bytes programados e depois silencio."""

    fluxo = b""          # definido por cada teste
    instancias = 0

    def __init__(self):
        self.port = self.baudrate = self.timeout = None
        self.dtr = self.rts = None
        self.is_open = False
        self._dados = b""
        self.escritos = b""

    def open(self):
        SerialFalsa.instancias += 1
        # so a primeira abertura recebe o fluxo, para a reconexao nao contar de novo
        self._dados = SerialFalsa.fluxo if SerialFalsa.instancias == 1 else b""
        self.is_open = True

    def close(self):
        self.is_open = False

    def reset_input_buffer(self):
        pass

    def read(self, n):
        if not self._dados:
            time.sleep(0.01)           # imita o timeout da serial de verdade
            return b""
        pedaco, self._dados = self._dados[:n], self._dados[n:]
        return pedaco

    def write(self, dados):
        self.escritos += dados


@pytest.fixture
def serial_falsa(monkeypatch):
    SerialFalsa.instancias = 0
    SerialFalsa.fluxo = b""
    monkeypatch.setattr(ponte.serial, "Serial", SerialFalsa)
    # o pulso de reset dorme 0,7 s; nos testes nao precisa
    monkeypatch.setattr(ponte.time, "sleep", lambda s: None)
    return SerialFalsa


def esperar(cond, segundos=3.0):
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if cond():
            return True
        time.sleep(0.01)
    return False


def test_le_quadros_em_sequencia(serial_falsa):
    serial_falsa.fluxo = quadro_serial(jpeg_de_teste(50)) + quadro_serial(jpeg_de_teste(200))
    cam = Camera("COMX")
    cam.iniciar()
    assert esperar(lambda: cam.quadros_lidos == 2)
    assert cam.quadro().mean() > 150          # o ultimo quadro e o claro
    assert cam.quadros_descartados == 0
    cam.parar()


def test_ressincroniza_apos_lixo(serial_falsa):
    """Log de boot da ESP32 e bytes perdidos nao podem travar a leitura."""
    lixo = b"ets Jul 29 2019\r\nrst:0x1 (POWERON)\xff\x00FR\xa5FRM"
    serial_falsa.fluxo = lixo + quadro_serial(jpeg_de_teste(90)) + b"\x00" * 7 + quadro_serial(jpeg_de_teste(90))
    cam = Camera("COMX")
    cam.iniciar()
    assert esperar(lambda: cam.quadros_lidos == 2)
    cam.parar()


def test_descarta_tamanho_absurdo(serial_falsa):
    invalido = MARCA + struct.pack("<I", 50 * 1024 * 1024)
    serial_falsa.fluxo = invalido + quadro_serial(jpeg_de_teste(90))
    cam = Camera("COMX")
    cam.iniciar()
    assert esperar(lambda: cam.quadros_lidos == 1)
    assert cam.quadros_descartados == 1
    cam.parar()


def test_descarta_jpeg_corrompido(serial_falsa):
    serial_falsa.fluxo = quadro_serial(b"isto nao e um jpeg") + quadro_serial(jpeg_de_teste(90))
    cam = Camera("COMX")
    cam.iniciar()
    assert esperar(lambda: cam.quadros_lidos == 1)
    assert cam.quadros_descartados == 1
    cam.parar()


def test_quadro_novo_so_entrega_uma_vez(serial_falsa):
    serial_falsa.fluxo = quadro_serial(jpeg_de_teste(90))
    cam = Camera("COMX")
    cam.iniciar()
    assert esperar(lambda: cam.quadros_lidos == 1)
    seq, q1 = cam.quadro_novo(-1)
    assert q1 is not None and seq == 1
    seq2, q2 = cam.quadro_novo(seq)
    assert q2 is None and seq2 == seq
    cam.parar()


def test_abre_com_dtr_e_rts_baixos(serial_falsa):
    """Com DTR/RTS altos a placa fica em reset. E o bug mais facil de reintroduzir."""
    cam = Camera("COMX", 921600)
    cam.iniciar()
    assert esperar(lambda: cam._serial is not None)
    assert cam._serial.dtr is False and cam._serial.rts is False
    assert cam._serial.baudrate == 921600
    cam.parar()


def test_comando_vai_com_quebra_de_linha(serial_falsa):
    cam = Camera("COMX")
    cam.iniciar()
    assert esperar(lambda: cam.conectada)
    cam.comando("L1")
    assert cam._serial.escritos == b"L1\n"
    cam.parar()
