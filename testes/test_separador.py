"""Envio do compartimento para o ESP32 dos servos (COM5)."""

import time

import pytest

import separador as modulo
from separador import Separador


class SerialFalsa:
    escritos: list[bytes] = []

    def __init__(self, *_, **__):
        self.is_open = True

    def reset_input_buffer(self): pass
    def read(self, n): return b""
    def flush(self): pass
    def close(self): self.is_open = False
    def write(self, dados): SerialFalsa.escritos.append(dados)


@pytest.fixture
def sep(monkeypatch):
    SerialFalsa.escritos = []
    monkeypatch.setattr(modulo.serial, "Serial", SerialFalsa)
    monkeypatch.setattr(modulo, "ESPERA_BOOT", 0)
    s = Separador("COM5")
    s.iniciar()
    yield s
    s.parar()


def esperar(condicao, segundos=3):
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if condicao():
            return True
        time.sleep(0.02)
    return False


def test_numeros_de_cada_forma(sep):
    for forma in ("circulo", "quadrado", "triangulo", "estrela"):
        assert sep.enviar(forma)
    assert esperar(lambda: len(SerialFalsa.escritos) == 4)
    assert SerialFalsa.escritos == [b"1", b"2", b"3", b"4"]


def test_outros_nao_aciona_servo(sep):
    assert sep.enviar("outros") is False
    time.sleep(0.3)
    assert SerialFalsa.escritos == []


def test_porta_ausente_nao_derruba(monkeypatch):
    def falha(*_, **__):
        raise modulo.serial.SerialException("COM5 nao existe")
    monkeypatch.setattr(modulo.serial, "Serial", falha)
    s = Separador("COM5")
    s.iniciar()
    assert esperar(lambda: s.ultimo_erro != "")
    assert s.enviar("circulo")      # entra na fila, sem travar quem chamou
    s.parar()
    assert not s.conectado
