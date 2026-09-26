#pragma once

#include <Arduino.h>
#include <atomic>
#include <functional>

#include "BluetoothA2DPSource.h"

// Plays mono PCM sources on a commercial Bluetooth speaker (ESP32 as A2DP source).
// A producer (main task) fills a lock-free ring buffer; the A2DP callback
// (Bluetooth task) resamples to 44.1 kHz and duplicates mono to stereo.
class BluetoothPlayer {
 public:
  bool begin();
  bool isConnected();
  bool waitForConnection(uint32_t timeoutMs);

  bool playWavFile(const char* path);
  bool playTone(uint16_t frequencyHz, uint16_t durationMs);

 private:
  using SampleProducer = std::function<size_t(int16_t*, size_t)>;

  bool runPlayback(uint32_t sourceSampleRate, const SampleProducer& producer);
  void prepareSource(uint32_t sourceSampleRate);
  bool waitUntilDrained(uint32_t timeoutMs);
  void stop();

  size_t pushSamples(const int16_t* samples, size_t count);
  bool popSample(int16_t& sample);
  uint32_t bufferedSamples() const;

  int32_t fillFrames(Frame* frames, int32_t frameCount);
  void finishFromCallback();

  static int32_t audioCallback(Frame* frames, int32_t frameCount);
  static void onConnectionStateChanged(esp_a2d_connection_state_t state, void* context);

  static BluetoothPlayer* _instance;

  BluetoothA2DPSource _source;
  int16_t* _ring = nullptr;
  std::atomic<uint32_t> _head{0};
  std::atomic<uint32_t> _tail{0};
  std::atomic<bool> _active{false};
  std::atomic<bool> _sourceFinished{false};
  std::atomic<bool> _drained{false};

  // Resampler state, only touched by the callback while _active is true.
  uint32_t _step = 0;
  uint32_t _fraction = 0;
  int16_t _current = 0;
  int16_t _next = 0;
  bool _primed = false;
  int32_t _gainQ8 = 256;
};
