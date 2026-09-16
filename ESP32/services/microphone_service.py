"""Microphone capture service for INMP441 audio responses on ESP32."""

import gc
import os
import struct

from machine import I2S, Pin
from time import sleep_ms

from config import (
    MIC_I2S_BUFFER_BYTES,
    MIC_I2S_ID,
    MIC_RAW_BUFFER_BYTES,
    MIC_RECORD_SECONDS,
    MIC_SAMPLE_RATE,
    MIC_SCK,
    MIC_SD,
    MIC_WS,
)


class MicrophoneService:
    """Capture PCM16 audio from the INMP441 using the tested I2S flow."""

    def __init__(
        self,
        i2s_id=MIC_I2S_ID,
        sck=MIC_SCK,
        ws=MIC_WS,
        sd=MIC_SD,
        sample_rate=MIC_SAMPLE_RATE,
        record_seconds=MIC_RECORD_SECONDS,
        raw_buffer_bytes=MIC_RAW_BUFFER_BYTES,
        i2s_buffer_bytes=MIC_I2S_BUFFER_BYTES,
    ):
        self._i2s_id = i2s_id
        self._sck = sck
        self._ws = ws
        self._sd = sd
        self._sample_rate = sample_rate
        self._record_seconds = record_seconds
        self._raw_buffer_bytes = raw_buffer_bytes
        self._pcm_chunk_bytes = raw_buffer_bytes // 2
        self._i2s_buffer_bytes = i2s_buffer_bytes
        self._i2s = None

    @property
    def sample_rate(self):
        return self._sample_rate

    @property
    def total_pcm_bytes(self):
        return self._sample_rate * self._record_seconds * 2

    def record_pcm16_to_file(self, destination_path):
        """Capture a fixed response window as PCM16 into a temporary file."""

        gc.collect()

        raw = bytearray(self._raw_buffer_bytes)
        pcm = bytearray(self._pcm_chunk_bytes)

        sent_bytes = 0
        peak_value = 0

        try:
            microphone = self._initialize_i2s()

            print("")
            print("GRABANDO RESPUESTA...")
            print("=== HABLA AHORA ===")
            print("Bytes esperados:", self.total_pcm_bytes)

            with open(destination_path, "wb") as pcm_file:
                while sent_bytes < self.total_pcm_bytes:
                    bytes_read = microphone.readinto(raw)

                    if not bytes_read:
                        continue

                    available_samples = bytes_read // 4
                    available_pcm_bytes = available_samples * 2
                    remaining_bytes = self.total_pcm_bytes - sent_bytes
                    pcm_bytes_to_write = min(available_pcm_bytes, remaining_bytes)
                    samples_to_convert = pcm_bytes_to_write // 2
                    pcm_position = 0

                    for index in range(samples_to_convert):
                        raw_position = index * 4
                        sample_32 = struct.unpack_from("<i", raw, raw_position)[0]
                        sample_16 = sample_32 >> 16
                        struct.pack_into("<h", pcm, pcm_position, sample_16)

                        absolute = abs(sample_16)
                        if absolute > peak_value:
                            peak_value = absolute

                        pcm_position += 2

                    pcm_file.write(memoryview(pcm)[:pcm_bytes_to_write])
                    sent_bytes += pcm_bytes_to_write

            file_size = os.stat(destination_path)[6]

            if file_size != self.total_pcm_bytes:
                raise OSError(
                    "Archivo PCM incompleto: esperados {} bytes, escritos {}.".format(
                        self.total_pcm_bytes,
                        file_size,
                    )
                )

            print("Audio capturado en archivo:", file_size, "bytes")
            print("Pico PCM16:", peak_value)
            return {
                "bytes_sent": file_size,
                "peak_pcm16": peak_value,
                "sample_rate": self._sample_rate,
            }
        finally:
            self.release()
            gc.collect()
            del raw
            del pcm
            gc.collect()

    def stream_pcm16_to_sink(self, sink):
        """Capture a fixed response window and stream PCM16 chunks to a sink."""

        gc.collect()

        raw = bytearray(self._raw_buffer_bytes)
        pcm = bytearray(self._pcm_chunk_bytes)

        sent_bytes = 0
        peak_value = 0

        try:
            microphone = self._initialize_i2s()

            print("")
            print("GRABANDO RESPUESTA...")
            print("=== HABLA AHORA ===")
            print("Bytes esperados:", self.total_pcm_bytes)

            while sent_bytes < self.total_pcm_bytes:
                bytes_read = microphone.readinto(raw)

                if not bytes_read:
                    continue

                available_samples = bytes_read // 4
                available_pcm_bytes = available_samples * 2
                remaining_bytes = self.total_pcm_bytes - sent_bytes
                pcm_bytes_to_send = min(available_pcm_bytes, remaining_bytes)
                samples_to_convert = pcm_bytes_to_send // 2
                pcm_position = 0

                for index in range(samples_to_convert):
                    raw_position = index * 4
                    sample_32 = struct.unpack_from("<i", raw, raw_position)[0]
                    sample_16 = sample_32 >> 16
                    struct.pack_into("<h", pcm, pcm_position, sample_16)

                    absolute = abs(sample_16)
                    if absolute > peak_value:
                        peak_value = absolute

                    pcm_position += 2

                sink(memoryview(pcm)[:pcm_bytes_to_send])
                sent_bytes += pcm_bytes_to_send

            print("Audio de respuesta capturado:", sent_bytes, "bytes")
            print("Pico PCM16:", peak_value)
            return {
                "bytes_sent": sent_bytes,
                "peak_pcm16": peak_value,
                "sample_rate": self._sample_rate,
            }
        finally:
            self.release()
            gc.collect()
            del raw
            del pcm
            gc.collect()

    def _initialize_i2s(self):
        """Initialize I2S RX for a single microphone capture lifecycle."""

        if self._i2s is not None:
            self.release()

        try:
            self._i2s = I2S(
                self._i2s_id,
                sck=Pin(self._sck),
                ws=Pin(self._ws),
                sd=Pin(self._sd),
                mode=I2S.RX,
                bits=32,
                format=I2S.MONO,
                rate=self._sample_rate,
                ibuf=self._i2s_buffer_bytes,
            )
            sleep_ms(150)
            return self._i2s
        except Exception:
            self.release()
            raise

    def release(self):
        """Deinitialize I2S RX and drop the driver reference."""

        if self._i2s is None:
            return

        microphone = self._i2s
        self._i2s = None

        try:
            microphone.deinit()
        except Exception:
            pass

        del microphone
        gc.collect()
        sleep_ms(300)
        sleep_ms(150)

    def close(self):
        """Release all hardware resources owned by the service."""

        self.release()

    def deinit(self):
        """Release all hardware resources owned by the service."""

        self.release()
