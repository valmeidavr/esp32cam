"""Escolha automatica da porta da ESP32-CAM."""

from types import SimpleNamespace

import pytest

import deteccao_porta


def porta(device, vid, pid, descricao="x"):
    return SimpleNamespace(device=device, vid=vid, pid=pid, description=descricao)


@pytest.fixture
def portas(monkeypatch):
    def _definir(lista):
        monkeypatch.setattr(deteccao_porta.list_ports, "comports", lambda: lista)
    return _definir


def test_acha_o_ch340(portas):
    portas([porta("COM1", 0x8087, 0x0001, "Intel"), porta("COM5", 0x1A86, 0x7523, "CH340")])
    escolhida, msg = deteccao_porta.encontrar()
    assert escolhida == "COM5"
    assert "CH340" in msg


def test_sem_nenhuma_porta(portas):
    portas([])
    escolhida, msg = deteccao_porta.encontrar()
    assert escolhida is None
    assert "cabo USB" in msg


def test_porta_desconhecida_nao_e_escolhida(portas):
    portas([porta("COM9", 0x1234, 0x5678, "Impressora")])
    escolhida, msg = deteccao_porta.encontrar()
    assert escolhida is None
    assert "COM9" in msg                      # mas aparece na dica


def test_duas_placas_usa_a_primeira_e_avisa(portas):
    portas([porta("COM3", 0x1A86, 0x7523), porta("COM4", 0x10C4, 0xEA60)])
    escolhida, msg = deteccao_porta.encontrar()
    assert escolhida == "COM3"
    assert "--porta" in msg


def test_porta_indicada_vence_a_deteccao(portas):
    portas([porta("COM3", 0x1A86, 0x7523)])
    escolhida, _ = deteccao_porta.encontrar("COM7")
    assert escolhida == "COM7"
