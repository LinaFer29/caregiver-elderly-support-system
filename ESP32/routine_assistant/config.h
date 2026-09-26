#pragma once

#include <Arduino.h>

// Central configuration for the ESP32 routine assistant (Arduino/C++ port).
// Only the "local" profile is supported: plain HTTP backend and MQTT without TLS.

// ===== Wi-Fi =====
constexpr char WIFI_SSID[] = "";
constexpr char WIFI_PASSWORD[] = "";
constexpr uint32_t WIFI_TIMEOUT_MS = 15000;
constexpr uint32_t WIFI_RETRY_DELAY_MS = 5000;

// ===== Backend (HTTP) =====
constexpr char BACKEND_HOST[] = "";
constexpr uint16_t BACKEND_PORT = 8000;
constexpr char AUDIO_ENDPOINT_PREFIX[] = "/assistant/audio/";
constexpr char STT_ENDPOINT[] = "/assistant/stt/";

constexpr uint32_t HTTP_CONNECT_TIMEOUT_MS = 15000;
constexpr uint32_t HTTP_READ_TIMEOUT_MS = 8000;
constexpr uint32_t HTTP_STT_TIMEOUT_MS = 120000;
constexpr size_t HTTP_STT_RESPONSE_MAX_BYTES = 4096;
constexpr size_t HTTP_IO_BUFFER_BYTES = 1024;

// ===== MQTT =====
constexpr char MQTT_BROKER[] = "";
constexpr uint16_t MQTT_PORT = 1884;
constexpr char MQTT_USER[] = "routine_assistant_local";
constexpr char MQTT_PASSWORD[] = "routine_assistant_local_password";
constexpr uint16_t MQTT_KEEPALIVE_SECONDS = 60;
constexpr uint32_t MQTT_RECONNECT_DELAY_MS = 5000;
constexpr uint32_t MQTT_CONNECT_TIMEOUT_MS = 10000;
constexpr char MQTT_TOPIC_PREFIX[] = "device";
constexpr char MQTT_TOPIC_SUFFIX[] = "audio";
constexpr uint16_t MQTT_BUFFER_BYTES = 1024;

// ===== Device identity =====
// WiFi.macAddress() returns "AA:BB:CC:DD:EE:FF". Set to true if the backend
// stores the MAC in lowercase (as MicroPython's hexlify() produced it).
constexpr bool MAC_ADDRESS_LOWERCASE = true;

// ===== LittleFS paths =====
constexpr char REMINDER_WAV_PATH[] = "/reminder.wav";
constexpr char RESPONSE_PCM_PATH[] = "/response.pcm";

// ===== Bluetooth speaker (A2DP source) =====
constexpr char BT_SPEAKER_NAME[] = "K-GP4W";
constexpr uint32_t BT_CONNECT_WAIT_MS = 20000;
constexpr uint32_t BT_OUTPUT_SAMPLE_RATE = 44100;
constexpr int32_t PLAYBACK_GAIN_PERCENT = 100;
constexpr uint32_t PLAYBACK_LEAD_IN_MS = 300;
constexpr uint32_t PLAYBACK_RING_SAMPLES = 2048;  // Must be a power of two.
constexpr uint32_t PLAYBACK_DRAIN_TIMEOUT_MS = 3000;

// ===== Feedback tones (played before and after recording) =====
constexpr bool ENABLE_FEEDBACK_TONES = true;
constexpr uint16_t TONE_FREQUENCY_HZ = 880;
constexpr uint16_t TONE_DURATION_MS = 150;
constexpr uint16_t TONE_GAP_MS = 80;
constexpr int16_t TONE_AMPLITUDE = 6000;
constexpr uint32_t TONE_SAMPLE_RATE = 16000;
constexpr uint32_t TONE_POST_DELAY_MS = 250;  // Covers Bluetooth output latency.

// ===== Touch sensor (TTP223B) =====
constexpr uint8_t TOUCH_PIN = 27;
constexpr uint8_t TOUCH_ACTIVE_LEVEL = HIGH;
constexpr uint32_t TOUCH_DEBOUNCE_MS = 50;
constexpr uint32_t TOUCH_WAIT_TIMEOUT_MS = 30000;
constexpr uint8_t REMINDER_REPEATS_ON_NO_TOUCH = 1;

// ===== Microphone (INMP441 over I2S) =====
constexpr uint8_t MIC_SCK = 14;
constexpr uint8_t MIC_WS = 15;
constexpr uint8_t MIC_SD = 32;
constexpr uint32_t MIC_SAMPLE_RATE = 16000;  // Contract with the backend STT.
constexpr uint32_t MIC_RECORD_SECONDS = 5;
constexpr uint8_t MIC_SAMPLE_SHIFT = 16;      // 32-bit I2S word -> PCM16 (same as MicroPython).
constexpr int32_t MIC_GAIN = 1;
constexpr int MIC_DMA_BUFFER_COUNT = 8;
constexpr int MIC_DMA_BUFFER_LEN = 256;
constexpr uint32_t MIC_WARMUP_MS = 150;
constexpr size_t MIC_READ_SAMPLES = 256;
