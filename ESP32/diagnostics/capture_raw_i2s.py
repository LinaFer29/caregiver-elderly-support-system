"""Capture raw I2S microphone bytes for offline diagnostics.

This script is intentionally standalone and is not imported by main.py.
It writes the exact bytes returned by machine.I2S.readinto() without PCM16
conversion, filtering, normalization, networking, playback, or backend calls.
"""

import gc
import os

from machine import I2S, Pin

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


RAW_OUTPUT_PATH = "/mic_raw_i2s.bin"


def capture_raw_i2s(output_path=RAW_OUTPUT_PATH):
    """Capture raw 32-bit mono I2S bytes directly to flash."""

    expected_bytes = MIC_SAMPLE_RATE * MIC_RECORD_SECONDS * 4
    captured_bytes = 0
    microphone = None
    raw = bytearray(MIC_RAW_BUFFER_BYTES)

    try:
        try:
            os.remove(output_path)
        except OSError:
            pass

        microphone = I2S(
            MIC_I2S_ID,
            sck=Pin(MIC_SCK),
            ws=Pin(MIC_WS),
            sd=Pin(MIC_SD),
            mode=I2S.RX,
            bits=32,
            format=I2S.MONO,
            rate=MIC_SAMPLE_RATE,
            ibuf=MIC_I2S_BUFFER_BYTES,
        )

        print("=== HABLA AHORA ===")

        with open(output_path, "wb") as raw_file:
            while captured_bytes < expected_bytes:
                bytes_read = microphone.readinto(raw)

                if not bytes_read:
                    continue

                remaining = expected_bytes - captured_bytes
                bytes_to_write = min(bytes_read, remaining)
                raw_file.write(memoryview(raw)[:bytes_to_write])
                captured_bytes += bytes_to_write

        actual_bytes = os.stat(output_path)[6]
        print("Captura RAW esperada:", expected_bytes, "bytes")
        print("Captura RAW obtenida:", actual_bytes, "bytes")

        if actual_bytes == expected_bytes:
            print("Captura completada.")
        else:
            print("Captura incompleta.")

        return actual_bytes
    finally:
        if microphone is not None:
            try:
                microphone.deinit()
            except Exception:
                pass

        del raw
        gc.collect()


capture_raw_i2s()
