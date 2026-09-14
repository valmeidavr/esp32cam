"""Confere que o binario do firmware que vai no instalador esta integro.

Nao grava nada: so verifica os cabecalhos que o bootloader da ESP32 espera.
"""

import os

import pytest

import gravador

AQUI = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(AQUI, "..", "visao", "firmware", "esp32cam-formas.bin")


def test_binario_existe_e_e_encontrado():
    assert os.path.isfile(BIN)
    assert gravador.caminho_do_binario() is not None


def test_tem_bootloader_e_aplicacao():
    """Imagens ESP32 comecam com 0xE9; o bootloader fica em 0x1000 e o app em 0x10000."""
    with open(BIN, "rb") as f:
        dados = f.read()
    assert len(dados) > 0x10000 + 1024
    assert dados[0x1000] == 0xE9, "bootloader ausente em 0x1000"
    assert dados[0x10000] == 0xE9, "aplicacao ausente em 0x10000"


def test_tabela_de_particoes():
    with open(BIN, "rb") as f:
        f.seek(0x8000)
        assert f.read(2) == b"\xaa\x50", "tabela de particoes ausente em 0x8000"
