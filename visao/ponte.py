"""Leitura dos quadros que a ESP32-CAM manda pela porta USB-serial."""

import struct
import threading
import time

import cv2
import numpy as np
import serial

MARCA = b"FRM\xa5"
TAMANHO_MAXIMO = 512 * 1024   # um quadro maior que isso so pode ser lixo


class Camera:
    """Le a serial numa thread e guarda sempre o quadro mais recente.

    Segurar so o ultimo quadro (em vez de uma fila) e proposital: se a
    deteccao atrasar, o que interessa e a imagem de agora, nao a de tres
    segundos atras.

    A thread tambem reabre a porta sozinha se o cabo for esbarrado ou a placa
    reiniciar — numa apresentacao nao da para pedir a plateia que espere
    enquanto alguem reinicia o programa.
    """

    def __init__(self, porta: str, baud: int = 921600):
        self.porta = porta
        self.baud = baud
        self._serial: serial.Serial | None = None
        self._quadro: np.ndarray | None = None
        self._trava = threading.Lock()
        self._rodando = False
        self.conectada = False
        self.quadros_lidos = 0
        self.quadros_descartados = 0
        self.ultimo_erro = ""
        self.sequencia = 0        # sobe a cada quadro novo

    # ------------------------------------------------------------- ciclo ---

    def iniciar(self) -> None:
        self._rodando = True
        threading.Thread(target=self._supervisor, daemon=True).start()

    def parar(self) -> None:
        self._rodando = False
        self._fechar()

    def esperar_conexao(self, segundos: float = 10.0) -> bool:
        """Bloqueia ate o primeiro quadro chegar. Devolve se conseguiu."""
        limite = time.monotonic() + segundos
        while time.monotonic() < limite:
            if self.quadro() is not None:
                return True
            time.sleep(0.1)
        return False

    def quadro(self) -> np.ndarray | None:
        with self._trava:
            return None if self._quadro is None else self._quadro.copy()

    def quadro_novo(self, ultima_sequencia: int) -> tuple[int, np.ndarray | None]:
        """Devolve (sequencia, quadro) so se chegou um quadro novo.

        Sem isso o laco de visao refaz a deteccao no mesmo quadro varias vezes
        entre uma chegada e outra: queima CPU e infla a taxa exibida.
        """
        with self._trava:
            if self._quadro is None or self.sequencia == ultima_sequencia:
                return ultima_sequencia, None
            return self.sequencia, self._quadro.copy()

    def comando(self, texto: str) -> None:
        """Manda um comando para a placa (ex: 'R6', 'Q12', 'L1')."""
        try:
            if self._serial and self._serial.is_open:
                self._serial.write(f"{texto}\n".encode())
        except (serial.SerialException, OSError):
            pass    # o supervisor ja vai perceber e reconectar

    # ----------------------------------------------------------- conexao ---

    def _abrir(self) -> None:
        # DTR e RTS estao ligados ao circuito de auto-reset da placa (EN e
        # GPIO0). Se a porta abrir com eles ativos — que e o padrao do
        # pyserial — a ESP32 fica presa em reset ou no modo de gravacao e nao
        # transmite nada. Por isso eles sao baixados ANTES do open().
        porta = serial.Serial()
        porta.port = self.porta
        porta.baudrate = self.baud
        porta.timeout = 2
        porta.dtr = False
        porta.rts = False
        porta.open()

        # Pulso curto em EN com GPIO0 solto: a placa reinicia em modo normal,
        # entao a leitura sempre comeca de um estado conhecido.
        porta.rts = True
        time.sleep(0.1)
        porta.rts = False
        time.sleep(0.6)
        porta.reset_input_buffer()

        self._serial = porta
        self.conectada = True
        self.ultimo_erro = ""

    def _fechar(self) -> None:
        self.conectada = False
        try:
            if self._serial and self._serial.is_open:
                self._serial.close()
        except Exception:
            pass
        self._serial = None

    def _supervisor(self) -> None:
        while self._rodando:
            try:
                self._abrir()
                self._ler_ate_falhar()
            except (serial.SerialException, OSError) as erro:
                self.ultimo_erro = str(erro)
            finally:
                self._fechar()

            if self._rodando:
                time.sleep(1.0)    # placa reiniciando ou cabo fora: tenta de novo

    # ------------------------------------------------------------ leitura ---

    def _sincronizar(self) -> bool:
        """Avanca byte a byte ate cair em cima da marca de inicio de quadro.

        E assim que a leitura se recupera do log de boot da ESP32 e de
        qualquer byte perdido no meio do caminho.
        """
        janela = b""
        while self._rodando:
            byte = self._serial.read(1)
            if not byte:
                return False
            janela = (janela + byte)[-4:]
            if janela == MARCA:
                return True
        return False

    def _ler_exato(self, quantidade: int) -> bytes | None:
        dados = self._serial.read(quantidade)
        return dados if len(dados) == quantidade else None

    def _ler_ate_falhar(self) -> None:
        silencios = 0

        while self._rodando:
            if not self._sincronizar():
                # Timeout de leitura. Alguns seguidos querem dizer que a placa
                # parou de falar de verdade; ai vale reabrir a porta.
                silencios += 1
                if silencios >= 3:
                    raise serial.SerialException("a placa parou de enviar quadros")
                continue
            silencios = 0

            cabecalho = self._ler_exato(4)
            if cabecalho is None:
                continue
            tamanho = struct.unpack("<I", cabecalho)[0]

            if not 0 < tamanho <= TAMANHO_MAXIMO:
                self.quadros_descartados += 1
                continue

            jpeg = self._ler_exato(tamanho)
            if jpeg is None:
                self.quadros_descartados += 1
                continue

            imagem = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
            if imagem is None:
                self.quadros_descartados += 1
                continue

            with self._trava:
                self._quadro = imagem
                self.sequencia += 1
            self.quadros_lidos += 1
