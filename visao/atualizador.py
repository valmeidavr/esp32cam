"""Atualizacao automatica a partir das releases do GitHub.

Ao abrir, o programa pergunta ao GitHub qual e a ultima versao publicada. Se
for mais nova que a instalada, baixa o instalador para a pasta temporaria e o
executa em modo silencioso; o instalador fecha o programa, troca os arquivos
e abre a versao nova sozinho.

Tudo aqui e "melhor esforco": sem internet, com o GitHub fora do ar ou com o
download falhando, o programa simplesmente abre a versao que ja tem.
"""

import json
import os
import subprocess
import sys
import tempfile
import urllib.request

from versao import REPOSITORIO, VERSAO

TEMPO_LIMITE = 4          # segundos; nao pode segurar a abertura do programa
API = f"https://api.github.com/repos/{REPOSITORIO}/releases/latest"


def _tupla(versao: str) -> tuple[int, ...]:
    """'v1.2.10' -> (1, 2, 10), para comparar sem cair no '1.10' < '1.9'."""
    limpa = versao.strip().lstrip("vV")
    partes = []
    for pedaco in limpa.split("."):
        digitos = "".join(c for c in pedaco if c.isdigit())
        partes.append(int(digitos) if digitos else 0)
    return tuple(partes)


def mais_nova(candidata: str, atual: str = VERSAO) -> bool:
    return _tupla(candidata) > _tupla(atual)


def consultar_ultima() -> dict | None:
    """Devolve {'versao', 'url', 'tamanho', 'nome'} da ultima release, ou None."""
    pedido = urllib.request.Request(API, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"ClassificadorESP32CAM/{VERSAO}",
    })
    with urllib.request.urlopen(pedido, timeout=TEMPO_LIMITE) as resposta:
        dados = json.load(resposta)

    for ativo in dados.get("assets", []):
        nome = ativo.get("name", "")
        if nome.lower().endswith(".exe") and "setup" in nome.lower():
            return {
                "versao": dados.get("tag_name", ""),
                "url": ativo["browser_download_url"],
                "tamanho": int(ativo.get("size", 0)),
                "nome": nome,
            }
    return None


def baixar(url: str, destino: str, tamanho_esperado: int, avisar=print) -> bool:
    pedido = urllib.request.Request(url, headers={"User-Agent": f"ClassificadorESP32CAM/{VERSAO}"})
    with urllib.request.urlopen(pedido, timeout=30) as resposta, open(destino, "wb") as arquivo:
        lidos = 0
        ultimo_pct = -1
        while True:
            pedaco = resposta.read(256 * 1024)
            if not pedaco:
                break
            arquivo.write(pedaco)
            lidos += len(pedaco)
            if tamanho_esperado:
                pct = lidos * 100 // tamanho_esperado
                if pct // 10 != ultimo_pct // 10:
                    avisar(f"  baixando... {pct}%")
                    ultimo_pct = pct

    # Um download cortado no meio e um instalador que nao abre; melhor
    # desistir e tentar na proxima vez.
    if tamanho_esperado and os.path.getsize(destino) != tamanho_esperado:
        os.remove(destino)
        return False
    return True


def executar_instalador(caminho: str) -> None:
    """Abre o instalador e sai do programa, para ele poder trocar os arquivos.

    /SILENT mostra so a barra de progresso; /CLOSEAPPLICATIONS fecha esta
    instancia; o proprio instalador reabre o programa ao terminar (entrada
    [Run] com postinstall, sem skipifsilent).
    """
    subprocess.Popen(
        [caminho, "/SILENT", "/CLOSEAPPLICATIONS", "/NORESTART", "/SUPPRESSMSGBOXES"],
        creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                    | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        close_fds=True,
    )


def verificar_e_atualizar(avisar=print) -> bool:
    """Devolve True se o instalador foi disparado e o programa deve encerrar."""
    if not getattr(sys, "frozen", False):
        return False       # rodando do fonte: quem atualiza e o git

    try:
        ultima = consultar_ultima()
    except Exception as erro:
        avisar(f"(sem verificar atualizacao: {type(erro).__name__})")
        return False

    if not ultima or not mais_nova(ultima["versao"]):
        avisar(f"versao {VERSAO} - atualizada.")
        return False

    avisar(f"\nNova versao disponivel: {ultima['versao']} (esta e a {VERSAO}).")
    destino = os.path.join(tempfile.gettempdir(), ultima["nome"])

    try:
        if not baixar(ultima["url"], destino, ultima["tamanho"], avisar):
            avisar("download incompleto; tento de novo na proxima abertura.")
            return False
        avisar("instalando a atualizacao... o programa reabre sozinho em instantes.")
        executar_instalador(destino)
        return True
    except Exception as erro:
        avisar(f"nao consegui atualizar agora ({type(erro).__name__}); abrindo a versao atual.")
        return False
