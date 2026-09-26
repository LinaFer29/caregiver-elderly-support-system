#include "WavFile.h"

#include <LittleFS.h>

namespace {

uint16_t readLe16(const uint8_t* data) {
  return (uint16_t)data[0] | ((uint16_t)data[1] << 8);
}

uint32_t readLe32(const uint8_t* data) {
  return (uint32_t)data[0] | ((uint32_t)data[1] << 8) | ((uint32_t)data[2] << 16) |
         ((uint32_t)data[3] << 24);
}

constexpr uint16_t WAV_FORMAT_PCM = 1;
constexpr uint16_t WAV_FORMAT_EXTENSIBLE = 0xFFFE;

}  // namespace

bool WavFile::readBytes(uint8_t* buffer, size_t length) {
  return _file.read(buffer, length) == length;
}

bool WavFile::skipBytes(uint32_t length) {
  return _file.seek(_file.position() + length);
}

bool WavFile::open(const char* path) {
  close();

  _file = LittleFS.open(path, "r");
  if (!_file) {
    Serial.printf("Error: no fue posible abrir %s\n", path);
    return false;
  }

  uint8_t header[12];
  if (!readBytes(header, sizeof(header)) || memcmp(header, "RIFF", 4) != 0 ||
      memcmp(header + 8, "WAVE", 4) != 0) {
    Serial.println("Error: el archivo no es un WAV RIFF válido.");
    close();
    return false;
  }

  bool formatFound = false;
  uint16_t audioFormat = 0;

  while (true) {
    uint8_t chunkHeader[8];
    if (!readBytes(chunkHeader, sizeof(chunkHeader))) {
      Serial.println("Error: el WAV no contiene bloque de datos.");
      close();
      return false;
    }

    const uint32_t chunkSize = readLe32(chunkHeader + 4);

    if (memcmp(chunkHeader, "fmt ", 4) == 0) {
      uint8_t format[16];
      if (chunkSize < sizeof(format) || !readBytes(format, sizeof(format))) {
        Serial.println("Error: bloque fmt inválido.");
        close();
        return false;
      }
      audioFormat = readLe16(format);
      _channels = readLe16(format + 2);
      _sampleRate = readLe32(format + 4);
      _bitsPerSample = readLe16(format + 14);
      formatFound = true;
      skipBytes(chunkSize - sizeof(format) + (chunkSize & 1));
      continue;
    }

    if (memcmp(chunkHeader, "data", 4) == 0) {
      const uint32_t available = _file.size() - _file.position();
      // TTS pipelines sometimes write 0 or 0xFFFFFFFF as data size.
      _dataBytes = (chunkSize == 0 || chunkSize > available) ? available : chunkSize;
      _dataRemaining = _dataBytes;
      break;
    }

    if (!skipBytes(chunkSize + (chunkSize & 1))) {
      Serial.println("Error: WAV truncado.");
      close();
      return false;
    }
  }

  const bool validFormat = formatFound &&
                           (audioFormat == WAV_FORMAT_PCM || audioFormat == WAV_FORMAT_EXTENSIBLE) &&
                           (_bitsPerSample == 8 || _bitsPerSample == 16) &&
                           (_channels == 1 || _channels == 2) && _sampleRate > 0;

  if (!validFormat) {
    Serial.printf("Error: formato WAV no soportado (formato %u, %u bits, %u canales).\n",
                  audioFormat, _bitsPerSample, _channels);
    close();
    return false;
  }

  return true;
}

void WavFile::close() {
  if (_file) {
    _file.close();
  }
  _dataRemaining = 0;
}

size_t WavFile::readMonoSamples(int16_t* output, size_t maxSamples) {
  if (!_file || _dataRemaining == 0 || maxSamples == 0) {
    return 0;
  }

  const size_t bytesPerFrame = (size_t)_channels * (_bitsPerSample / 8);
  size_t frames = sizeof(_raw) / bytesPerFrame;
  if (frames > maxSamples) {
    frames = maxSamples;
  }
  if (frames > _dataRemaining / bytesPerFrame) {
    frames = _dataRemaining / bytesPerFrame;
  }
  if (frames == 0) {
    _dataRemaining = 0;
    return 0;
  }

  const size_t bytesRead = _file.read(_raw, frames * bytesPerFrame);
  frames = bytesRead / bytesPerFrame;
  _dataRemaining = (bytesRead == 0) ? 0 : _dataRemaining - bytesRead;

  for (size_t i = 0; i < frames; ++i) {
    const uint8_t* frame = _raw + i * bytesPerFrame;
    int32_t left;
    int32_t right;

    if (_bitsPerSample == 16) {
      left = (int16_t)readLe16(frame);
      right = (_channels == 2) ? (int16_t)readLe16(frame + 2) : left;
    } else {
      left = ((int32_t)frame[0] - 128) << 8;
      right = (_channels == 2) ? (((int32_t)frame[1] - 128) << 8) : left;
    }

    output[i] = (int16_t)((left + right) / 2);
  }

  return frames;
}
