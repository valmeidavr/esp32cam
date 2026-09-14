"""ESP32-CAM: le a camera pelo cabo USB, identifica as formas que passam na
esteira e mostra em qual compartimento cada uma cai.

    python app.py                  acha a placa sozinho e abre o navegador
    python app.py --porta COM7     forca uma porta
    python app.py --so-local       nao aceita acesso de outros aparelhos
    python app.py --demo           esteira simulada, sem precisar da placa
    python app.py --gravar         regrava o firmware na placa
"""

import argparse
import json
import sys
import threading
import time
import traceback
import webbrowser
from collections import Counter, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import cv2

import cena
import deteccao_porta
import rede
from detector import detectar
from pagina import PAGINA
from ponte import Camera
from rastreador import Rastreador
from versao import VERSAO

LIMITE = b"--quadro"
COMPARTIMENTOS = ("circulo", "quadrado", "triangulo", "estrela", "outros")


class Estado:
    """O que o laco de visao produz e o servidor web consome."""

    def __init__(self):
        self.trava = threading.Lock()
        self.jpeg: bytes | None = None
        self.fps = 0.0
        self.quadros_processados = 0   # a pagina vigia isto para saber se o video parou
        self.area_minima = 700
        self.mostrar_linha = True

        self.rastreador = Rastreador(largura=320)
        self.contagens = Counter({c: 0 for c in COMPARTIMENTOS})
        self.eventos: deque = deque(maxlen=40)
        self.serie = 0            # sobe a cada despejo; a pagina usa para animar
        self.pecas_visiveis: list[dict] = []

    def zerar(self) -> None:
        with self.trava:
            self.contagens = Counter({c: 0 for c in COMPARTIMENTOS})
            self.eventos.clear()
            self.rastreador.zerar()


estado = Estado()
camera: Camera | None = None


def laco_de_visao() -> None:
    """Detecta, rastreia e desenha — uma vez por quadro novo.

    Nada que acontecer com um quadro pode derrubar esta thread: se ela morre,
    o video congela no ultimo quadro e o programa parece travado. Um erro e
    registrado no console e o quadro seguinte segue normalmente.
    """
    ultima_sequencia = -1
    ultimo_instante = time.monotonic()
    media_fps = 0.0
    erros_seguidos = 0

    while True:
        sequencia, quadro = camera.quadro_novo(ultima_sequencia)
        if quadro is None:
            time.sleep(0.005)
            continue
        ultima_sequencia = sequencia

        try:
            _processar_quadro(quadro)
            erros_seguidos = 0
        except Exception:
            erros_seguidos += 1
            if erros_seguidos <= 3:       # nao inundar o console se for todo quadro
                print("\n[visao] erro ao processar um quadro (o video continua):")
                traceback.print_exc()
            continue

        agora = time.monotonic()
        intervalo = agora - ultimo_instante
        ultimo_instante = agora
        if intervalo > 0:
            # Media exponencial: o numero na tela para de tremer a cada quadro.
            media_fps = 0.9 * media_fps + 0.1 * (1.0 / intervalo)
        with estado.trava:
            estado.fps = media_fps


def _processar_quadro(quadro) -> None:
    formas = detectar(quadro, area_minima=estado.area_minima)

    with estado.trava:
        rastreador = estado.rastreador
        rastreador.largura = quadro.shape[1]
        despejos = rastreador.atualizar(formas)
        for d in despejos:
            estado.contagens[d.compartimento] += 1
            estado.serie += 1
            estado.eventos.appendleft({
                "id": d.id, "forma": d.forma,
                "compartimento": d.compartimento,
                "confianca": d.confianca, "instante": d.instante,
            })
        pecas = rastreador.pecas
        linha = rastreador.linha
        mostrar_linha = estado.mostrar_linha

    anotado = cena.desenhar(quadro, pecas, linha, mostrar_linha)
    ok, buffer = cv2.imencode(".jpg", anotado, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not ok:
        return

    with estado.trava:
        estado.jpeg = buffer.tobytes()
        estado.quadros_processados += 1
        estado.pecas_visiveis = [
            {"id": p.id, "forma": p.nome, "confianca": round(p.confianca, 2),
             "contada": p.contada, "centro": p.centro}
            for p in pecas
        ]


class Servidor(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass    # o console fica para as mensagens do programa, nao para o access log

    def do_GET(self):
        rota = urlparse(self.path)
        consulta = parse_qs(rota.query)

        if rota.path == "/":
            self._enviar(PAGINA.encode("utf-8"), "text/html; charset=utf-8")
        elif rota.path == "/stream":
            self._transmitir()
        elif rota.path == "/estado":
            self._enviar(self._instantaneo(), "application/json")
        elif rota.path == "/ajuste":
            self._ajustar(consulta)
            self._enviar(b"ok", "text/plain")
        elif rota.path == "/zerar":
            estado.zerar()
            self._enviar(b"ok", "text/plain")
        else:
            self.send_error(404)

    # ---------------------------------------------------------- auxiliares ---

    def _enviar(self, corpo: bytes, tipo: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _instantaneo(self) -> bytes:
        with estado.trava:
            dados = {
                "contagens": dict(estado.contagens),
                "total": sum(estado.contagens.values()),
                "serie": estado.serie,
                "eventos": list(estado.eventos)[:12],
                "pecas": estado.pecas_visiveis,
                "fps": round(estado.fps, 1),
                "quadros": camera.quadros_lidos,
                "processados": estado.quadros_processados,
                "perdidos": camera.quadros_descartados,
                "conectada": camera.conectada,
                "porta": camera.porta,
                "linha": estado.rastreador.linha,
                "modo": estado.rastreador.modo,
                "area": estado.area_minima,
                "versao": VERSAO,
            }
        return json.dumps(dados).encode()

    def _ajustar(self, consulta: dict) -> None:
        with estado.trava:
            if "area" in consulta:
                estado.area_minima = max(100, int(consulta["area"][0]))
            if "linha" in consulta:
                estado.rastreador.definir_linha(int(consulta["linha"][0]))
            if "modo" in consulta:
                estado.rastreador.definir_modo(consulta["modo"][0])
            if "mostrar_linha" in consulta:
                estado.mostrar_linha = consulta["mostrar_linha"][0] == "1"
        if "qualidade" in consulta:
            camera.comando(f"Q{int(consulta['qualidade'][0])}")
        if "flash" in consulta:
            camera.comando(f"L{int(consulta['flash'][0])}")

    def _transmitir(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=quadro")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        ultimo = None
        try:
            while True:
                with estado.trava:
                    jpeg = estado.jpeg
                if jpeg is None or jpeg is ultimo:
                    time.sleep(0.01)
                    continue
                ultimo = jpeg

                self.wfile.write(
                    LIMITE + b"\r\nContent-Type: image/jpeg\r\n"
                    + f"Content-Length: {len(jpeg)}\r\n\r\n".encode()
                    + jpeg + b"\r\n"
                )
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass    # aba fechada


def _pausar_se_clicado() -> None:
    """Sem isso a janela some antes de a pessoa ler o erro, quando o programa
    e aberto pelo atalho em vez do terminal."""
    if sys.stdin and sys.stdin.isatty():
        try:
            input("\npressione ENTER para fechar...")
        except EOFError:
            pass


def main() -> int:
    global camera

    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("--porta", default=None,
                            help="porta serial (padrao: descobre sozinho)")
    argumentos.add_argument("--baud", type=int, default=921600)
    argumentos.add_argument("--http", type=int, default=8000)
    argumentos.add_argument("--so-local", action="store_true",
                            help="aceitar so este PC, sem acesso pela rede")
    argumentos.add_argument("--sem-navegador", action="store_true")
    argumentos.add_argument("--demo", action="store_true",
                            help="esteira simulada, para testar sem a placa")
    argumentos.add_argument("--sem-atualizar", action="store_true",
                            help="nao procurar versao nova no GitHub ao abrir")
    argumentos.add_argument("--gravar", action="store_true",
                            help="regravar o firmware na placa e sair")
    opcoes = argumentos.parse_args()

    print("=" * 60)
    print(f"  ESP32-CAM  -  classificacao de pecas na esteira   v{VERSAO}")
    print("  ETPC - Escola Tecnica  |  (c) 2026 Todos os direitos reservados")
    print("  Matheus Pedrosa, Carlos Eduardo Borges, Maria Eduarda Mazza,")
    print("  Milena Maia, Milena Rodrigues  |  Apoio: Prof. Vinicius")
    print("=" * 60)

    if not opcoes.sem_atualizar and not opcoes.gravar:
        import atualizador
        if atualizador.verificar_e_atualizar():
            return 0        # o instalador assume daqui e reabre o programa

    if opcoes.demo:
        from fonte_demo import EsteiraSimulada
        print("\nMODO DEMONSTRACAO: esteira simulada, sem a placa.")
        camera = EsteiraSimulada()
        porta = camera.porta
    else:
        porta, explicacao = deteccao_porta.encontrar(opcoes.porta)
        print(f"\n{explicacao}")
        if porta is None:
            _pausar_se_clicado()
            return 1

        if opcoes.gravar:
            import gravador
            ok = gravador.gravar(porta)
            _pausar_se_clicado()
            return 0 if ok else 1

        camera = Camera(porta, opcoes.baud)
    camera.iniciar()

    print("aguardando o primeiro quadro...")
    if not camera.esperar_conexao(12.0):
        print("\nA placa nao enviou nenhum quadro.")
        print("  - o firmware esta gravado?  rode de novo com --gravar")
        print("  - a camera esta bem encaixada no conector?")
        print(f"  - alguem mais esta usando a {porta}? (monitor serial, Arduino IDE)")
        if camera.ultimo_erro:
            print(f"  - ultimo erro da serial: {camera.ultimo_erro}")
        camera.parar()
        _pausar_se_clicado()
        return 1

    print("camera respondendo.")
    threading.Thread(target=laco_de_visao, daemon=True).start()

    endereco_escuta = "127.0.0.1" if opcoes.so_local else "0.0.0.0"
    try:
        servidor = ThreadingHTTPServer((endereco_escuta, opcoes.http), Servidor)
    except OSError:
        print(f"\nA porta {opcoes.http} ja esta em uso. "
              f"Feche a outra janela do programa ou rode com --http 8001.")
        camera.parar()
        _pausar_se_clicado()
        return 1

    local = f"http://localhost:{opcoes.http}/"
    print(f"\n  neste PC:       {local}")
    if not opcoes.so_local:
        ip = rede.ip_local()
        if ip:
            print(f"  outros aparelhos:  http://{ip}:{opcoes.http}/   (celular, notebook da banca)")
        else:
            print("  (nao consegui descobrir o IP desta maquina na rede)")
    print("\n  feche esta janela para encerrar\n")

    if not opcoes.sem_navegador:
        threading.Timer(1.0, lambda: webbrowser.open(local)).start()

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nencerrando...")
    finally:
        camera.parar()
        servidor.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
