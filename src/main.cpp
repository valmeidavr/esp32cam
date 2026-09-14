// ESP32-CAM (AI-Thinker): envia os quadros da camera pela porta USB-serial.
// Quem decodifica, detecta as formas e mostra no navegador e o programa
// Python em visao/. A placa nao usa Wi-Fi.
//
// Formato de cada quadro na serial:
//
//     "FRM\xA5"   4 bytes de marca, para o PC se reencontrar apos qualquer ruido
//     tamanho     4 bytes, uint32 little-endian
//     jpeg        <tamanho> bytes
//
// Comandos aceitos do PC (uma letra + numero + '\n'):
//
//     R<0-13>   resolucao (framesize)
//     Q<10-63>  qualidade JPEG (menor = melhor imagem, mais bytes)
//     L<0|1>    LED de flash

#include <Arduino.h>
#include <esp_camera.h>

#include "camera_pins.h"

static const uint32_t BAUD = 921600;
static const uint8_t  MARCA[4] = {'F', 'R', 'M', 0xA5};

static bool iniciarCamera() {
  camera_config_t cfg = {};
  cfg.ledc_channel = LEDC_CHANNEL_0;
  cfg.ledc_timer   = LEDC_TIMER_0;
  cfg.pin_d0 = Y2_GPIO_NUM;    cfg.pin_d1 = Y3_GPIO_NUM;
  cfg.pin_d2 = Y4_GPIO_NUM;    cfg.pin_d3 = Y5_GPIO_NUM;
  cfg.pin_d4 = Y6_GPIO_NUM;    cfg.pin_d5 = Y7_GPIO_NUM;
  cfg.pin_d6 = Y8_GPIO_NUM;    cfg.pin_d7 = Y9_GPIO_NUM;
  cfg.pin_xclk  = XCLK_GPIO_NUM;
  cfg.pin_pclk  = PCLK_GPIO_NUM;
  cfg.pin_vsync = VSYNC_GPIO_NUM;
  cfg.pin_href  = HREF_GPIO_NUM;
  cfg.pin_sccb_sda = SIOD_GPIO_NUM;
  cfg.pin_sccb_scl = SIOC_GPIO_NUM;
  cfg.pin_pwdn  = PWDN_GPIO_NUM;
  cfg.pin_reset = RESET_GPIO_NUM;
  cfg.xclk_freq_hz = 20000000;
  cfg.pixel_format = PIXFORMAT_JPEG;
  cfg.grab_mode    = CAMERA_GRAB_LATEST;

  // A serial e o gargalo (921600 baud ~= 90 KB/s), nao a camera. QVGA a
  // qualidade media da uns 8 KB por quadro, ou seja ~10 fps — de sobra para
  // detectar formas geometricas.
  cfg.frame_size   = FRAMESIZE_QVGA;
  cfg.jpeg_quality = 12;
  if (psramFound()) {
    cfg.fb_count    = 2;
    cfg.fb_location = CAMERA_FB_IN_PSRAM;
  } else {
    cfg.fb_count    = 1;
    cfg.fb_location = CAMERA_FB_IN_DRAM;
  }

  if (esp_camera_init(&cfg) != ESP_OK) return false;

  // O sensor da AI-Thinker costuma vir montado de cabeca para baixo.
  sensor_t *s = esp_camera_sensor_get();
  s->set_vflip(s, 1);
  s->set_hmirror(s, 1);
  return true;
}

static void tratarComandos() {
  while (Serial.available()) {
    int letra = Serial.read();
    if (letra != 'R' && letra != 'Q' && letra != 'L') continue;

    // parseInt para no '\n' ou no timeout; o PC sempre manda a quebra de linha.
    long valor = Serial.parseInt();
    sensor_t *s = esp_camera_sensor_get();

    switch (letra) {
      case 'R': s->set_framesize(s, (framesize_t)constrain(valor, 0, 13)); break;
      case 'Q': s->set_quality(s, constrain(valor, 10, 63));               break;
      case 'L': digitalWrite(FLASH_GPIO_NUM, valor ? HIGH : LOW);          break;
    }
  }
}

void setup() {
  Serial.begin(BAUD);
  Serial.setDebugOutput(false);
  Serial.setTimeout(50);

  pinMode(FLASH_GPIO_NUM, OUTPUT);
  digitalWrite(FLASH_GPIO_NUM, LOW);

  // Sem camera nao ha nada a fazer: pisca o flash devagar e reinicia, assim da
  // para perceber o problema sem abrir o monitor serial.
  if (!iniciarCamera()) {
    for (int i = 0; i < 6; i++) {
      digitalWrite(FLASH_GPIO_NUM, i % 2);
      delay(300);
    }
    digitalWrite(FLASH_GPIO_NUM, LOW);
    delay(2000);
    ESP.restart();
  }
}

void loop() {
  tratarComandos();

  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    delay(10);
    return;
  }

  uint32_t tamanho = fb->len;
  Serial.write(MARCA, sizeof(MARCA));
  Serial.write((const uint8_t *)&tamanho, sizeof(tamanho));
  Serial.write(fb->buf, fb->len);

  esp_camera_fb_return(fb);
}
