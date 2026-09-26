#include "BluetoothPlayer.h"

#include <math.h>

#include "WavFile.h"
#include "config.h"

BluetoothPlayer* BluetoothPlayer::_instance = nullptr;

namespace {

static_assert((PLAYBACK_RING_SAMPLES & (PLAYBACK_RING_SAMPLES - 1)) == 0,
              "PLAYBACK_RING_SAMPLES must be a power of two");

constexpr uint32_t RING_MASK = PLAYBACK_RING_SAMPLES - 1;
constexpr size_t PRODUCER_CHUNK_SAMPLES = 256;
constexpr uint32_t STALL_TIMEOUT_MS = 3000;
constexpr uint32_t FIXED_ONE = 1UL << 16;
constexpr float TWO_PI_F = 6.28318530718f;

int16_t clampToInt16(int32_t value) {
  if (value > 32767) return 32767;
  if (value < -32768) return -32768;
  return (int16_t)value;
}

void writeSilence(Frame* frames, int32_t from, int32_t to) {
  for (int32_t i = from; i < to; ++i) {
    frames[i].channel1 = 0;
    frames[i].channel2 = 0;
  }
}

}  // namespace

bool BluetoothPlayer::begin() {
  if (_ring == nullptr) {
    _ring = static_cast<int16_t*>(malloc(PLAYBACK_RING_SAMPLES * sizeof(int16_t)));
    if (_ring == nullptr) {
      Serial.println("Error: sin memoria para el buffer de reproducción.");
      return false;
    }
  }

  _instance = this;
  _gainQ8 = (PLAYBACK_GAIN_PERCENT * 256) / 100;

  _source.set_on_connection_state_changed(onConnectionStateChanged, this);
  _source.set_auto_reconnect(true);
  // Only Bluetooth Classic (A2DP) is used: return the BLE controller memory
  // (~30 KB) to the heap so Wi-Fi, MQTT and HTTP have room to work.
  _source.set_reset_ble(true);

  Serial.printf("Iniciando Bluetooth A2DP. Buscando parlante \"%s\"...\n", BT_SPEAKER_NAME);
  // Between playbacks the callback streams silence, which keeps the link alive.
  _source.start(BT_SPEAKER_NAME, audioCallback);
  return true;
}

bool BluetoothPlayer::isConnected() {
  return _source.is_connected();
}

bool BluetoothPlayer::waitForConnection(uint32_t timeoutMs) {
  const uint32_t start = millis();
  while (!isConnected()) {
    if (millis() - start >= timeoutMs) {
      return false;
    }
    delay(200);
  }
  return true;
}

bool BluetoothPlayer::playWavFile(const char* path) {
  WavFile wav;
  if (!wav.open(path)) {
    return false;
  }

  Serial.printf("WAV: %lu Hz, %u bits, %u canal(es), %lu bytes de audio\n",
                (unsigned long)wav.sampleRate(), wav.bitsPerSample(), wav.channels(),
                (unsigned long)wav.dataBytes());

  // The link is already streaming silence; this pause lets the speaker settle
  // so the first syllable of the reminder is not cut.
  delay(PLAYBACK_LEAD_IN_MS);

  const bool played = runPlayback(wav.sampleRate(), [&wav](int16_t* buffer, size_t maxSamples) {
    return wav.readMonoSamples(buffer, maxSamples);
  });

  wav.close();
  return played;
}

bool BluetoothPlayer::playTone(uint16_t frequencyHz, uint16_t durationMs) {
  const uint32_t totalSamples = (TONE_SAMPLE_RATE * durationMs) / 1000;
  const uint32_t fadeSamples = TONE_SAMPLE_RATE / 200;  // 5 ms fade to avoid clicks.
  const float phaseIncrement = TWO_PI_F * frequencyHz / TONE_SAMPLE_RATE;
  uint32_t generated = 0;
  float phase = 0.0f;

  return runPlayback(TONE_SAMPLE_RATE, [&](int16_t* buffer, size_t maxSamples) {
    size_t count = 0;
    while (count < maxSamples && generated < totalSamples) {
      float envelope = 1.0f;
      if (generated < fadeSamples) {
        envelope = (float)generated / fadeSamples;
      } else if (totalSamples - generated < fadeSamples) {
        envelope = (float)(totalSamples - generated) / fadeSamples;
      }
      buffer[count++] = (int16_t)(sinf(phase) * TONE_AMPLITUDE * envelope);
      phase += phaseIncrement;
      if (phase >= TWO_PI_F) {
        phase -= TWO_PI_F;
      }
      ++generated;
    }
    return count;
  });
}

bool BluetoothPlayer::runPlayback(uint32_t sourceSampleRate, const SampleProducer& producer) {
  if (!isConnected()) {
    Serial.println("Error: el parlante Bluetooth no está conectado.");
    return false;
  }

  prepareSource(sourceSampleRate);

  int16_t chunk[PRODUCER_CHUNK_SAMPLES];
  size_t pending = 0;
  size_t offset = 0;
  uint32_t lastProgress = millis();

  while (true) {
    if (offset >= pending) {
      pending = producer(chunk, PRODUCER_CHUNK_SAMPLES);
      offset = 0;
      if (pending == 0) {
        break;
      }
    }

    const size_t written = pushSamples(chunk + offset, pending - offset);
    offset += written;

    // Start consuming once half of the ring is filled to absorb jitter.
    if (!_active.load() && bufferedSamples() >= PLAYBACK_RING_SAMPLES / 2) {
      _active.store(true);
    }

    if (written > 0) {
      lastProgress = millis();
      continue;
    }

    _active.store(true);
    if (!isConnected() || millis() - lastProgress > STALL_TIMEOUT_MS) {
      Serial.println("Error: reproducción interrumpida (parlante desconectado o sin avance).");
      stop();
      return false;
    }
    delay(2);
  }

  const uint32_t remaining = bufferedSamples();
  _sourceFinished.store(true);
  _active.store(true);

  const uint32_t drainTimeout =
      (remaining * 1000UL) / sourceSampleRate + PLAYBACK_DRAIN_TIMEOUT_MS;
  const bool drained = waitUntilDrained(drainTimeout);
  stop();

  if (!drained) {
    Serial.println("Advertencia: la reproducción no terminó dentro del tiempo esperado.");
  }
  return drained;
}

void BluetoothPlayer::prepareSource(uint32_t sourceSampleRate) {
  _active.store(false);
  delay(20);  // Let any in-flight callback finish before resetting its state.

  _head.store(0);
  _tail.store(0);
  _sourceFinished.store(false);
  _drained.store(false);
  _primed = false;
  _fraction = 0;
  _step = (uint32_t)(((uint64_t)sourceSampleRate << 16) / BT_OUTPUT_SAMPLE_RATE);
}

bool BluetoothPlayer::waitUntilDrained(uint32_t timeoutMs) {
  const uint32_t start = millis();
  while (!_drained.load()) {
    if (!isConnected() || millis() - start >= timeoutMs) {
      return false;
    }
    delay(5);
  }
  return true;
}

void BluetoothPlayer::stop() {
  _active.store(false);
}

size_t BluetoothPlayer::pushSamples(const int16_t* samples, size_t count) {
  const uint32_t head = _head.load();
  const uint32_t tail = _tail.load();
  const uint32_t freeSpace = PLAYBACK_RING_SAMPLES - (head - tail);
  const size_t toWrite = count < freeSpace ? count : freeSpace;

  for (size_t i = 0; i < toWrite; ++i) {
    _ring[(head + i) & RING_MASK] = samples[i];
  }
  _head.store(head + toWrite);
  return toWrite;
}

bool BluetoothPlayer::popSample(int16_t& sample) {
  const uint32_t tail = _tail.load();
  if (tail == _head.load()) {
    return false;
  }
  sample = _ring[tail & RING_MASK];
  _tail.store(tail + 1);
  return true;
}

uint32_t BluetoothPlayer::bufferedSamples() const {
  return _head.load() - _tail.load();
}

void BluetoothPlayer::finishFromCallback() {
  _active.store(false);
  _drained.store(true);
}

int32_t BluetoothPlayer::fillFrames(Frame* frames, int32_t frameCount) {
  if (!_active.load()) {
    writeSilence(frames, 0, frameCount);
    return frameCount;
  }

  if (!_primed) {
    int16_t first;
    if (!popSample(first)) {
      if (_sourceFinished.load()) {
        finishFromCallback();
      }
      writeSilence(frames, 0, frameCount);
      return frameCount;
    }
    int16_t second;
    _current = first;
    _next = popSample(second) ? second : first;
    _fraction = 0;
    _primed = true;
  }

  for (int32_t i = 0; i < frameCount; ++i) {
    // Linear interpolation between the current and next source samples.
    const int32_t delta = (int32_t)_next - (int32_t)_current;
    int32_t sample = _current + (int32_t)(((int64_t)delta * _fraction) >> 16);
    sample = (sample * _gainQ8) >> 8;

    const int16_t output = clampToInt16(sample);
    frames[i].channel1 = output;  // Mono -> stereo.
    frames[i].channel2 = output;

    _fraction += _step;
    while (_fraction >= FIXED_ONE) {
      _fraction -= FIXED_ONE;
      _current = _next;

      int16_t incoming;
      if (popSample(incoming)) {
        _next = incoming;
      } else if (_sourceFinished.load()) {
        finishFromCallback();
        writeSilence(frames, i + 1, frameCount);
        return frameCount;
      } else {
        _next = _current;  // Underrun: hold the last sample until data arrives.
      }
    }
  }

  return frameCount;
}

int32_t BluetoothPlayer::audioCallback(Frame* frames, int32_t frameCount) {
  if (_instance == nullptr) {
    writeSilence(frames, 0, frameCount);
    return frameCount;
  }
  return _instance->fillFrames(frames, frameCount);
}

void BluetoothPlayer::onConnectionStateChanged(esp_a2d_connection_state_t state, void* context) {
  BluetoothPlayer* player = static_cast<BluetoothPlayer*>(context);
  if (player != nullptr) {
    Serial.printf("Bluetooth: %s\n", player->_source.to_str(state));
  }
}
