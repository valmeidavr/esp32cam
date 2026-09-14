"""O servidor web inteiro, rodando sobre a esteira simulada."""

import json
import socket
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app
from fonte_demo import EsteiraSimulada


def porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def servidor():
    app.camera = EsteiraSimulada(fps=30, velocidade=6.0)
    app.camera.iniciar()
    assert app.camera.esperar_conexao(5)
    threading.Thread(target=app.laco_de_visao, daemon=True).start()

    porta = porta_livre()
    srv = ThreadingHTTPServer(("127.0.0.1", porta), app.Servidor)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{porta}"
    srv.shutdown()
    app.camera.parar()


def pegar(base, rota):
    r = urllib.request.urlopen(base + rota, timeout=5)
    return r.status, r.headers, r.read()


def test_pagina_principal(servidor):
    status, cab, corpo = pegar(servidor, "/")
    assert status == 200 and "text/html" in cab["Content-Type"]
    assert b'id="caixa"' in corpo and b"/stream" in corpo


def test_estado_tem_todos_os_campos(servidor):
    _, _, corpo = pegar(servidor, "/estado")
    d = json.loads(corpo)
    for campo in ("contagens", "total", "serie", "eventos", "pecas", "fps",
                  "conectada", "porta", "linha", "modo", "area"):
        assert campo in d, campo
    assert set(d["contagens"]) == {"circulo", "quadrado", "triangulo", "estrela", "outros"}
    assert d["porta"] == "demo" and d["conectada"] is True


def test_stream_entrega_jpeg(servidor):
    r = urllib.request.urlopen(servidor + "/stream", timeout=5)
    assert "multipart/x-mixed-replace" in r.headers["Content-Type"]
    pedaco = r.read(8000)
    assert b"--quadro" in pedaco and b"\xff\xd8" in pedaco
    r.close()


def test_ajustes_refletem_no_estado(servidor):
    pegar(servidor, "/ajuste?linha=250&modo=saida&area=1200")
    d = json.loads(pegar(servidor, "/estado")[2])
    assert d["linha"] == 250 and d["modo"] == "saida" and d["area"] == 1200
    pegar(servidor, "/ajuste?linha=192&modo=linha&area=700")     # devolve o padrao


def test_esteira_simulada_gera_contagens(servidor):
    """Em alguns segundos as pecas desenhadas cruzam a linha e entram na conta."""
    limite = time.monotonic() + 25
    while time.monotonic() < limite:
        d = json.loads(pegar(servidor, "/estado")[2])
        if d["total"] >= 2:
            break
        time.sleep(0.3)
    assert d["total"] >= 2
    assert d["serie"] == d["total"]
    assert len(d["eventos"]) == d["total"]
    assert all(e["compartimento"] in d["contagens"] for e in d["eventos"])


def test_zerar(servidor):
    pegar(servidor, "/zerar")
    d = json.loads(pegar(servidor, "/estado")[2])
    assert d["total"] == 0 and d["eventos"] == []


def test_rota_inexistente(servidor):
    with pytest.raises(urllib.error.HTTPError) as erro:
        pegar(servidor, "/nada")
    assert erro.value.code == 404
