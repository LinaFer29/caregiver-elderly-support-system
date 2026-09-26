#include "ActivityService.h"

#include <LittleFS.h>

#include "config.h"

ActivityService::ActivityService(HttpService& http, BluetoothPlayer& player,
                                 Microphone& microphone, TouchSensor& touch)
    : _http(http), _player(player), _microphone(microphone), _touch(touch) {}

bool ActivityService::process(const Activity& activity, const String& macAddress) {
  printActivity(activity);

  Serial.println();
  Serial.println("Descargando audio del recordatorio...");
  if (!_http.downloadAudio(activity.audioFile, REMINDER_WAV_PATH)) {
    Serial.println("No fue posible descargar el audio del recordatorio.");
    cleanupFiles();
    return false;
  }

  if (!_player.waitForConnection(BT_CONNECT_WAIT_MS)) {
    Serial.println("Parlante Bluetooth no conectado. La actividad permanece pendiente.");
    cleanupFiles();
    return false;
  }

  if (!playReminderAndWaitForTouch()) {
    Serial.println("Sin respuesta del adulto mayor. La actividad permanece pendiente.");
    cleanupFiles();
    return false;
  }

  playFeedbackTones(1);  // Recording starts.
  CaptureInfo capture;
  const bool recorded = _microphone.recordToFile(RESPONSE_PCM_PATH, capture);
  playFeedbackTones(2);  // Recording finished.

  if (!recorded) {
    Serial.println("Error al capturar la respuesta de voz.");
    cleanupFiles();
    return false;
  }

  SttResult result;
  const bool submitted = _http.submitResponseFile(macAddress, activity.assignmentId,
                                                  _microphone.sampleRate(), RESPONSE_PCM_PATH,
                                                  result);
  cleanupFiles();

  if (!submitted) {
    Serial.println("No fue posible procesar la respuesta hablada.");
    return false;
  }

  printResult(result, capture);
  return true;
}

bool ActivityService::playReminderAndWaitForTouch() {
  const uint8_t attempts = 1 + REMINDER_REPEATS_ON_NO_TOUCH;

  for (uint8_t attempt = 1; attempt <= attempts; ++attempt) {
    Serial.printf("Reproduciendo recordatorio (intento %u de %u)...\n", attempt, attempts);
    if (!_player.playWavFile(REMINDER_WAV_PATH)) {
      Serial.println("Error durante la reproducción del audio.");
      return false;
    }
    Serial.println("Reproducción terminada.");

    Serial.printf("Toca el sensor para responder (máximo %lu s)...\n",
                  (unsigned long)(TOUCH_WAIT_TIMEOUT_MS / 1000));
    if (_touch.waitForPress(TOUCH_WAIT_TIMEOUT_MS)) {
      return true;
    }
    Serial.println("No se detectó toque.");
  }

  return false;
}

void ActivityService::playFeedbackTones(uint8_t count) {
  if (!ENABLE_FEEDBACK_TONES) {
    return;
  }
  for (uint8_t i = 0; i < count; ++i) {
    _player.playTone(TONE_FREQUENCY_HZ, TONE_DURATION_MS);
    if (i + 1 < count) {
      delay(TONE_GAP_MS);
    }
  }
  // Bluetooth adds output latency: wait so the tone is not captured by the mic.
  delay(TONE_POST_DELAY_MS);
}

void ActivityService::printActivity(const Activity& activity) {
  Serial.println();
  Serial.println("Actividad recibida:");
  Serial.printf("ID assignment: %ld\n", activity.assignmentId);
  Serial.printf("Actividad: %s\n", activity.activity.c_str());
  Serial.printf("Mensaje: %s\n", activity.message.c_str());
  Serial.printf("Hora programada: %s\n", activity.scheduledTime.c_str());
  Serial.printf("Audio: %s\n", activity.audioFile.c_str());
}

void ActivityService::printResult(const SttResult& result, const CaptureInfo& capture) {
  Serial.println();
  Serial.println("Resultado de la respuesta:");
  Serial.printf("Assignment: %ld\n", result.assignmentId);
  Serial.printf("Transcripción: %s\n", result.transcription.c_str());
  Serial.printf("Resultado: %s\n", result.result.c_str());
  Serial.printf("Estado final: %s\n", result.assignmentStatus.c_str());
  Serial.printf("Actualizada: %s\n", result.assignmentUpdated ? "true" : "false");
  Serial.printf("Pico PCM16 capturado: %ld\n", (long)capture.peakPcm16);
}

void ActivityService::cleanupFiles() {
  LittleFS.remove(REMINDER_WAV_PATH);
  LittleFS.remove(RESPONSE_PCM_PATH);
}
