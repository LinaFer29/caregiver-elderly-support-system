#pragma once

#include <Arduino.h>
#include <FS.h>

// Streaming PCM WAV reader (8-bit unsigned or 16-bit signed, mono or stereo)
// that always returns mono PCM16 samples.
class WavFile {
 public:
  bool open(const char* path);
  void close();

  // Returns the number of mono samples written to output (0 at end of data).
  size_t readMonoSamples(int16_t* output, size_t maxSamples);

  uint32_t sampleRate() const { return _sampleRate; }
  uint16_t channels() const { return _channels; }
  uint16_t bitsPerSample() const { return _bitsPerSample; }
  uint32_t dataBytes() const { return _dataBytes; }

 private:
  bool readBytes(uint8_t* buffer, size_t length);
  bool skipBytes(uint32_t length);

  File _file;
  uint32_t _sampleRate = 0;
  uint16_t _channels = 0;
  uint16_t _bitsPerSample = 0;
  uint32_t _dataBytes = 0;
  uint32_t _dataRemaining = 0;
  uint8_t _raw[512];
};
