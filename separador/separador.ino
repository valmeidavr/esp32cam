// ESP32 do separador: recebe do PC o compartimento de cada peca e move a
// cacamba ate ele com dois servos.
//
//   servo de GIRO     (embaixo)  gira o braco esquerda/direita e leva a
//                                cacamba para cima do compartimento certo
//   servo de DESPEJO  (em cima)  vira a cacamba para a peca cair (um lado so)
//
// A caixa vista de cima, igual a pagina do programa:
//
//     +-------------+-------------+
//     | 1 circulo   | 2 quadrado  |
//     +-------------+-------------+  <== braco com a cacamba
//     | 3 triangulo | 4 estrela   |
//     +-------------+-------------+
//
// Comandos que chegam pela USB-serial (115200 baud):
//
//     1 a 4     despeja a peca no compartimento (o programa do PC manda isto)
//     ?         responde "SEPARADOR" — e assim que o PC descobre a porta
//     G<graus>  so move o servo de giro    (calibrar pelo monitor serial)
//     D<graus>  so move o servo de despejo (calibrar pelo monitor serial)
//
// Ciclo de cada peca: espera ela cair na cacamba -> gira ate o compartimento
// -> vira a cacamba -> desvira -> volta ao repouso, embaixo da esteira.
//
// Para calibrar: feche o programa do PC, abra o Monitor Serial do Arduino IDE
// em 115200, mande G e D com varios angulos ate achar os certos e copie os
// numeros para as tabelas abaixo.

#include <Arduino.h>

// ------------------------------------------------------------ ligacoes ---
static const int PINO_GIRO    = 18;
static const int PINO_DESPEJO = 19;

// ------------------------------------------------------------- angulos ---
// Servo de giro: posicao da cacamba em cima de cada compartimento.
static const int GIRO_REPOUSO = 90;            // embaixo da saida da esteira
static const int GIRO_COMPARTIMENTO[5] = {
  GIRO_REPOUSO,  // 0: nao usado
  70,            // 1 circulo
  55,            // 2 quadrado
  110,           // 3 triangulo
  125,           // 4 estrela
};

// Servo de despejo: cacamba em pe (segurando a peca) e virada (despejando).
static const int DESPEJO_REPOUSO = 0;
static const int DESPEJO_VIRADO  = 120;

// -------------------------------------------------------------- tempos ---
static const unsigned long ESPERA_QUEDA_MS  = 700;  // da linha de despejo ate a peca cair na cacamba
static const unsigned long PAUSA_DESPEJO_MS = 600;  // cacamba virada, a peca escorregando
static const unsigned long PAUSA_ASSENTAR_MS = 150; // servo chegou, deixa o braco parar de balancar
static const int MS_POR_GRAU_GIRO = 6;              // giro devagar: a peca nao voa da cacamba

static const uint32_t BAUD = 115200;

// ----------------------------------------------------------- servos ---
// PWM direto pelo LEDC, sem biblioteca externa: 50 Hz, pulso de 0,5 a 2,4 ms.
static const int FREQ_SERVO = 50;
static const int BITS_PWM   = 14;
static const int PULSO_MIN_US = 500;
static const int PULSO_MAX_US = 2400;

#if ESP_ARDUINO_VERSION_MAJOR < 3
static int canalDoPino(int pino) { return pino == PINO_GIRO ? 4 : 5; }
#endif

static void prenderServo(int pino) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcAttach(pino, FREQ_SERVO, BITS_PWM);
#else
  ledcSetup(canalDoPino(pino), FREQ_SERVO, BITS_PWM);
  ledcAttachPin(pino, canalDoPino(pino));
#endif
}

static void escreverAngulo(int pino, int graus) {
  graus = constrain(graus, 0, 180);
  uint32_t pulso = map(graus, 0, 180, PULSO_MIN_US, PULSO_MAX_US);
  uint32_t duty  = pulso * ((1UL << BITS_PWM) - 1) / (1000000UL / FREQ_SERVO);
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(pino, duty);
#else
  ledcWrite(canalDoPino(pino), duty);
#endif
}

static int anguloGiro = GIRO_REPOUSO;

// Anda grau a grau: um tranco do servo arremessa a peca para fora da cacamba.
static void girarAte(int destino) {
  destino = constrain(destino, 0, 180);
  while (anguloGiro != destino) {
    anguloGiro += (destino > anguloGiro) ? 1 : -1;
    escreverAngulo(PINO_GIRO, anguloGiro);
    delay(MS_POR_GRAU_GIRO);
  }
  delay(PAUSA_ASSENTAR_MS);
}

static void despejarEm(int compartimento) {
  delay(ESPERA_QUEDA_MS);

  girarAte(GIRO_COMPARTIMENTO[compartimento]);
  escreverAngulo(PINO_DESPEJO, DESPEJO_VIRADO);
  delay(PAUSA_DESPEJO_MS);
  escreverAngulo(PINO_DESPEJO, DESPEJO_REPOUSO);
  delay(PAUSA_ASSENTAR_MS);
  girarAte(GIRO_REPOUSO);

  Serial.printf("OK %d\n", compartimento);
}

// ---------------------------------------------------------- comandos ---
// Enquanto um despejo acontece, os comandos seguintes esperam no buffer da
// serial e sao atendidos em ordem — duas pecas seguidas nao se perdem.
static void tratarComandos() {
  while (Serial.available()) {
    int letra = Serial.read();

    if (letra >= '1' && letra <= '4') {
      despejarEm(letra - '0');
    } else if (letra == '?') {
      Serial.println("SEPARADOR");
    } else if (letra == 'G' || letra == 'g') {
      int graus = constrain(Serial.parseInt(), 0, 180);
      girarAte(graus);
      Serial.printf("giro %d\n", graus);
    } else if (letra == 'D' || letra == 'd') {
      int graus = constrain(Serial.parseInt(), 0, 180);
      escreverAngulo(PINO_DESPEJO, graus);
      Serial.printf("despejo %d\n", graus);
    }
    // '\n', '\r' e qualquer outra coisa: ignorados
  }
}

void setup() {
  Serial.begin(BAUD);
  Serial.setTimeout(50);

  prenderServo(PINO_GIRO);
  prenderServo(PINO_DESPEJO);
  escreverAngulo(PINO_DESPEJO, DESPEJO_REPOUSO);
  escreverAngulo(PINO_GIRO, GIRO_REPOUSO);

  Serial.println("SEPARADOR pronto");
}

void loop() {
  tratarComandos();
  delay(2);
}
