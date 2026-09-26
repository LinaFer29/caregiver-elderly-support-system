#pragma once

#include <Arduino.h>

#include "Activity.h"
#include "config.h"

// INMP441 capture over I2S (32-bit words, left channel) converted to PCM16 mono.
class Microphone {
 public:
  bool begin();
  bool recordToFile(const char* path, CaptureInfo& info);

  uint32_t sampleRate() const { return MIC_SAMPLE_RATE; }
  uint32_t totalPcmBytes() const { return MIC_SAMPLE_RATE * MIC_RECORD_SECONDS * 2; }

 private:
  void discard(uint32_t durationMs);

  bool _installed = false;
  int32_t _raw[MIC_READ_SAMPLES];
  int16_t _pcm[MIC_READ_SAMPLES];
};
