"""Atualizacao automatica: comparacao de versoes e fluxo com o GitHub simulado."""

import io
import json
import sys

import pytest

import atualizador


@pytest.mark.parametrize("candidata, atual, esperado", [
    ("v1.0.1", "1.0.0", True),
    ("1.0.1", "1.0.1", False),
    ("v1.0.0", "1.0.1", False),
    ("v1.10.0", "1.9.9", True),          # nao pode comparar como texto
    ("v2", "1.99.99", True),
    ("lixo", "1.0.0", False),
])
def test_mais_nova(candidata, atual, esperado):
    assert atualizador.mais_nova(candidata, atual) is esperado


class RespostaFalsa(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


@pytest.fixture
def github(monkeypatch):
    """Simula a API e o download; devolve um dicionario com o que aconteceu."""
    registro = {"instalador_executado": None}
    corpo_exe = b"MZ" + b"\0" * 998

    def urlopen(pedido, timeout=None):
        url = pedido.full_url if hasattr(pedido, "full_url") else pedido
        if url.endswith("/releases/latest"):
            return RespostaFalsa(json.dumps({
                "tag_name": registro["tag"],
                "assets": [
                    {"name": "outra-coisa.zip", "browser_download_url": "x", "size": 1},
                    {"name": "ClassificadorESP32CAM-Setup-9.9.9.exe",
                     "browser_download_url": "https://exemplo/setup.exe",
                     "size": len(corpo_exe)},
                ],
            }).encode())
        if url == "https://exemplo/setup.exe":
            return RespostaFalsa(corpo_exe)
        raise AssertionError(url)

    monkeypatch.setattr(atualizador.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(atualizador, "executar_instalador",
                        lambda caminho: registro.__setitem__("instalador_executado", caminho))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    return registro


def test_atualiza_quando_ha_versao_nova(github, tmp_path, monkeypatch):
    monkeypatch.setattr(atualizador.tempfile, "gettempdir", lambda: str(tmp_path))
    github["tag"] = "v9.9.9"
    mensagens = []
    assert atualizador.verificar_e_atualizar(mensagens.append) is True
    assert github["instalador_executado"].endswith("ClassificadorESP32CAM-Setup-9.9.9.exe")
    assert (tmp_path / "ClassificadorESP32CAM-Setup-9.9.9.exe").stat().st_size == 1000
    assert any("Nova versao" in m for m in mensagens)


def test_nao_atualiza_quando_ja_esta_na_ultima(github):
    github["tag"] = "v" + atualizador.VERSAO
    assert atualizador.verificar_e_atualizar(lambda *_: None) is False
    assert github["instalador_executado"] is None


def test_sem_internet_segue_normal(monkeypatch):
    def falha(*_, **__):
        raise OSError("sem rede")
    monkeypatch.setattr(atualizador.urllib.request, "urlopen", falha)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    mensagens = []
    assert atualizador.verificar_e_atualizar(mensagens.append) is False
    assert any("sem verificar" in m for m in mensagens)


def test_rodando_do_fonte_nao_verifica(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    chamou = []
    monkeypatch.setattr(atualizador, "consultar_ultima", lambda: chamou.append(1))
    assert atualizador.verificar_e_atualizar(lambda *_: None) is False
    assert chamou == []


def test_download_incompleto_e_descartado(github, tmp_path, monkeypatch):
    monkeypatch.setattr(atualizador.tempfile, "gettempdir", lambda: str(tmp_path))
    github["tag"] = "v9.9.9"
    original = atualizador.urllib.request.urlopen

    def cortado(pedido, timeout=None):
        r = original(pedido, timeout)
        url = pedido.full_url if hasattr(pedido, "full_url") else pedido
        return RespostaFalsa(r.read()[:500]) if url.endswith("setup.exe") else r

    monkeypatch.setattr(atualizador.urllib.request, "urlopen", cortado)
    assert atualizador.verificar_e_atualizar(lambda *_: None) is False
    assert github["instalador_executado"] is None
    assert not (tmp_path / "ClassificadorESP32CAM-Setup-9.9.9.exe").exists()
