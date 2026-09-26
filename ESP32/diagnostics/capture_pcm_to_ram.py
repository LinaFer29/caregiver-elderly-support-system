"""Capture PCM16 microphone audio to RAM before writing it to flash.

This diagnostic script is standalone and is not imported by main.py. It avoids
all flash writes while I2S is active so the captured PCM can be compared against
the product flow.
"""

import gc
import os
import struct

from machine import I2S, Pin

from config import (
    MIC_I2S_BUFFER_BYTES,
    MIC_I2S_ID,
    MIC_RAW_BUFFER_BYTES,
    MIC_SAMPLE_RATE,
    MIC_SCK,
    MIC_SD,
    MIC_WS,
)


OUTPUT_PATH = "/mic_ram_capture_stable.pcm"
CAPTURE_SECONDS_X10 = 15
EXPECTED_PCM_BYTES = MIC_SAMPLE_RATE * CAPTURE_SECONDS_X10 * 2 // 10
DISCARD_RAW_BYTES = MIC_SAMPLE_RATE * 4 * 4 // 10
MIN_FREE_BYTES = 60000


def capture_pcm_to_ram(output_path=OUTPUT_PATH):
    """Capture 1.5 seconds of PCM16 to RAM, then write it to flash."""

    gc.collect()
    heap_before = gc.mem_free()
    print("Heap antes buffer:", heap_before)

    if heap_before < MIN_FREE_BYTES:
        print("Memoria insuficiente para captura RAM.")
        return None

    capture_buffer = bytearray(EXPECTED_PCM_BYTES)
    gc.collect()
    print("Heap después buffer:", gc.mem_free())

    raw = bytearray(MIC_RAW_BUFFER_BYTES)
    pcm = bytearray(MIC_RAW_BUFFER_BYTES // 2)
    microphone = None
    captured_bytes = 0

    try:
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

        discarded_bytes = 0

        while discarded_bytes < DISCARD_RAW_BYTES:
            bytes_read = microphone.readinto(raw)

            if bytes_read:
                discarded_bytes += bytes_read

        print("I2S estabilizado. Bytes descartados:", discarded_bytes)

        print("=== HABLA AHORA ===")

        while captured_bytes < EXPECTED_PCM_BYTES:
            bytes_read = microphone.readinto(raw)

            if not bytes_read:
                continue

            available_samples = bytes_read // 4
            available_pcm_bytes = available_samples * 2
            remaining_bytes = EXPECTED_PCM_BYTES - captured_bytes
            pcm_bytes_to_copy = min(available_pcm_bytes, remaining_bytes)
            samples_to_convert = pcm_bytes_to_copy // 2
            pcm_position = 0

            for index in range(samples_to_convert):
                raw_position = index * 4
                sample_32 = struct.unpack_from("<i", raw, raw_position)[0]
                sample_16 = sample_32 >> 16
                struct.pack_into("<h", pcm, pcm_position, sample_16)
                pcm_position += 2

            capture_buffer[
                captured_bytes:captured_bytes + pcm_bytes_to_copy
            ] = memoryview(pcm)[:pcm_bytes_to_copy]
            captured_bytes += pcm_bytes_to_copy

        print("PCM capturado en RAM:", captured_bytes, "bytes")
    finally:
        if microphone is not None:
            try:
                microphone.deinit()
            except Exception:
                pass
            microphone = None

        gc.collect()
        print("I2S cerrado.")

    try:
        os.remove(output_path)
    except OSError:
        pass

    with open(output_path, "wb") as output_file:
        output_file.write(capture_buffer)

    actual_bytes = os.stat(output_path)[6]
    print("Archivo escrito después de cerrar I2S:", actual_bytes, "bytes")
    return actual_bytes


capture_pcm_to_ram()
