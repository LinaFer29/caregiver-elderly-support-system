#include "Microphone.h"

#include <LittleFS.h>
#include <driver/i2s.h>

namespace {

constexpr i2s_port_t MIC_PORT = I2S_NUM_0;
constexpr uint8_t MAX_CONSECUTIVE_READ_FAILURES = 5;

}  // namespace

bool Microphone::begin() {
  i2s_config_t config = {};
  config.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);
  config.sample_rate = MIC_SAMPLE_RATE;
  config.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;
  config.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;
  config.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  config.intr_alloc_flags = 0;
  config.dma_buf_count = MIC_DMA_BUFFER_COUNT;
  config.dma_buf_len = MIC_DMA_BUFFER_LEN;
  config.use_apll = false;

  i2s_pin_config_t pins = {};
  pins.mck_io_num = I2S_PIN_NO_CHANGE;  // Otherwise MCLK would be routed to GPIO0.
  pins.bck_io_num = MIC_SCK;
  pins.ws_io_num = MIC_WS;
  pins.data_out_num = I2S_PIN_NO_CHANGE;
  pins.data_in_num = MIC_SD;

  if (i2s_driver_install(MIC_PORT, &config, 0, nullptr) != ESP_OK) {
    Serial.println("Error: no fue posible instalar el driver I2S.");
    return false;
  }

  if (i2s_set_pin(MIC_PORT, &pins) != ESP_OK) {
    Serial.println("Error: no fue posible configurar los pines I2S.");
    i2s_driver_uninstall(MIC_PORT);
    return false;
  }

  _installed = true;
  Serial.printf("INMP441 listo (%lu Hz).\n", (unsigned long)MIC_SAMPLE_RATE);
  return true;
}

void Microphone::discard(uint32_t durationMs) {
  // The DMA ring keeps filling between captures; drop stale audio first.
  size_t bytesToDiscard = (size_t)MIC_SAMPLE_RATE * 4 * durationMs / 1000 +
                          (size_t)MIC_DMA_BUFFER_COUNT * MIC_DMA_BUFFER_LEN * 4;

  while (bytesToDiscard > 0) {
    size_t bytesRead = 0;
    i2s_read(MIC_PORT, _raw, sizeof(_raw), &bytesRead, pdMS_TO_TICKS(100));
    if (bytesRead == 0) {
      break;
    }
    bytesToDiscard = bytesRead >= bytesToDiscard ? 0 : bytesToDiscard - bytesRead;
  }
}

bool Microphone::recordToFile(const char* path, CaptureInfo& info) {
  info = CaptureInfo();
  info.sampleRate = MIC_SAMPLE_RATE;

  if (!_installed) {
    Serial.println("Error: el micrófono no está inicializado.");
    return false;
  }

  LittleFS.remove(path);
  File file = LittleFS.open(path, "w");
  if (!file) {
    Serial.println("Error: no fue posible crear el archivo PCM de respuesta.");
    return false;
  }

  discard(MIC_WARMUP_MS);

  const uint32_t totalBytes = totalPcmBytes();
  uint32_t writtenBytes = 0;
  int32_t peak = 0;
  uint8_t failures = 0;

  Serial.println();
  Serial.println("GRABANDO RESPUESTA...");
  Serial.println("=== HABLA AHORA ===");
  Serial.printf("Bytes esperados: %lu\n", (unsigned long)totalBytes);

  while (writtenBytes < totalBytes) {
    size_t bytesRead = 0;
    const esp_err_t status =
        i2s_read(MIC_PORT, _raw, sizeof(_raw), &bytesRead, pdMS_TO_TICKS(1000));

    if (status != ESP_OK || bytesRead == 0) {
      if (++failures >= MAX_CONSECUTIVE_READ_FAILURES) {
        Serial.println("Error: el micrófono dejó de entregar datos.");
        file.close();
        LittleFS.remove(path);
        return false;
      }
      continue;
    }
    failures = 0;

    size_t samples = bytesRead / sizeof(int32_t);
    const size_t remainingSamples = (totalBytes - writtenBytes) / sizeof(int16_t);
    if (samples > remainingSamples) {
      samples = remainingSamples;
    }

    for (size_t i = 0; i < samples; ++i) {
      int32_t value = (_raw[i] >> MIC_SAMPLE_SHIFT) * MIC_GAIN;
      if (value > 32767) value = 32767;
      if (value < -32768) value = -32768;

      const int32_t magnitude = value < 0 ? -value : value;
      if (magnitude > peak) {
        peak = magnitude;
      }
      _pcm[i] = (int16_t)value;
    }

    const size_t chunkBytes = samples * sizeof(int16_t);
    if (file.write(reinterpret_cast<const uint8_t*>(_pcm), chunkBytes) != chunkBytes) {
      Serial.println("Error: no fue posible escribir el audio en LittleFS.");
      file.close();
      LittleFS.remove(path);
      return false;
    }
    writtenBytes += chunkBytes;
  }

  file.close();

  info.bytesWritten = writtenBytes;
  info.peakPcm16 = peak;

  Serial.printf("Audio capturado en archivo: %lu bytes\n", (unsigned long)writtenBytes);
  Serial.printf("Pico PCM16: %ld\n", (long)peak);
  return true;
}
