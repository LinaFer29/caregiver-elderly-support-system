"""Audio playback service for WAV files on ESP32 MicroPython."""

import gc
import struct

from machine import DAC, Pin
from time import sleep_ms, ticks_add, ticks_diff, ticks_us

from config import MAX_DAC_RATE, PIN_AUDIO, VOLUMEN_PORCENTAJE


class AudioService:
    """Encapsulate WAV validation and playback through DAC GPIO25."""

    def __init__(
        self,
        pin_audio=PIN_AUDIO,
        max_dac_rate=MAX_DAC_RATE,
        volumen_porcentaje=VOLUMEN_PORCENTAJE,
    ):
        self._pin_audio = pin_audio
        self._max_dac_rate = max_dac_rate
        self._volumen_porcentaje = volumen_porcentaje
        self._dac = None

    def read_wav_info(self, path):
        """Read WAV container metadata without loading the full file in RAM."""

        with open(path, "rb") as audio_file:
            header = audio_file.read(12)

            if len(header) != 12:
                raise ValueError("Archivo WAV demasiado pequeño.")

            if header[0:4] != b"RIFF":
                raise ValueError("El archivo no comienza con RIFF.")

            if header[8:12] != b"WAVE":
                raise ValueError("El archivo no contiene cabecera WAVE.")

            fmt_info = None
            data_position = None
            data_size = None

            while True:
                chunk_header = audio_file.read(8)

                if len(chunk_header) < 8:
                    break

                chunk_id = chunk_header[0:4]
                chunk_size = struct.unpack("<I", chunk_header[4:8])[0]

                if chunk_id == b"fmt ":
                    if chunk_size < 16:
                        raise ValueError("El chunk fmt del WAV es inválido.")

                    fmt_data = audio_file.read(chunk_size)
                    if len(fmt_data) != chunk_size:
                        raise ValueError("El chunk fmt del WAV está incompleto.")

                    fmt_info = {
                        "formato_audio": struct.unpack_from("<H", fmt_data, 0)[0],
                        "canales": struct.unpack_from("<H", fmt_data, 2)[0],
                        "frecuencia": struct.unpack_from("<I", fmt_data, 4)[0],
                        "bytes_por_segundo": struct.unpack_from("<I", fmt_data, 8)[0],
                        "alineacion": struct.unpack_from("<H", fmt_data, 12)[0],
                        "bits": struct.unpack_from("<H", fmt_data, 14)[0],
                    }

                    if chunk_size & 1:
                        audio_file.read(1)
                elif chunk_id == b"data":
                    data_position = audio_file.tell()
                    data_size = chunk_size
                    break
                else:
                    audio_file.seek(chunk_size + (chunk_size & 1), 1)

            if fmt_info is None:
                raise ValueError("El WAV no contiene chunk fmt.")

            if data_position is None:
                raise ValueError("El WAV no contiene chunk data.")

            return {
                "formato_audio": fmt_info["formato_audio"],
                "canales": fmt_info["canales"],
                "frecuencia": fmt_info["frecuencia"],
                "bytes_por_segundo": fmt_info["bytes_por_segundo"],
                "alineacion": fmt_info["alineacion"],
                "bits": fmt_info["bits"],
                "posicion_datos": data_position,
                "tamano_datos": data_size,
            }

    def validate_wav(self, info):
        """Validate that the WAV can be reproduced by the current hardware flow."""

        if info["formato_audio"] != 1:
            raise ValueError(
                "WAV no compatible: formato {}. Se requiere PCM lineal.".format(
                    info["formato_audio"]
                )
            )

        if info["bits"] not in (8, 16):
            raise ValueError(
                "WAV no compatible: {} bits. Se permiten 8 o 16.".format(
                    info["bits"]
                )
            )

        if info["canales"] not in (1, 2):
            raise ValueError(
                "WAV no compatible: {} canales.".format(info["canales"])
            )

        bytes_per_sample = info["bits"] // 8
        expected_alignment = info["canales"] * bytes_per_sample

        if info["alineacion"] != expected_alignment:
            raise ValueError(
                "Alineación WAV inesperada: {}.".format(info["alineacion"])
            )

        if info["tamano_datos"] <= 0:
            raise ValueError("El chunk data del WAV no contiene audio.")

        if info["bits"] == 16 and (info["tamano_datos"] % expected_alignment) != 0:
            raise ValueError(
                "El chunk data del WAV no está alineado a frames PCM16."
            )

    def play_wav(self, path):
        """Read, validate and play a WAV file through DAC GPIO25."""

        info = self.read_wav_info(path)
        self.validate_wav(info)

        print("")
        print("Información WAV:")
        print("  PCM:", info["formato_audio"])
        print("  Canales:", info["canales"])
        print("  Frecuencia:", info["frecuencia"], "Hz")
        print("  Bits:", info["bits"])
        print("  Datos:", info["tamano_datos"], "bytes")

        if (
            info["bits"] == 8
            and info["canales"] == 1
            and info["frecuencia"] == 8000
        ):
            print("Usando reproducción optimizada PCM U8 / 8 kHz.")
            self._play_pcm_u8_8k(path, info)
        else:
            print("Usando reproducción de compatibilidad PCM16.")
            self._play_pcm16_compatible(path, info)

        print("Memoria libre después de reproducir:", gc.mem_free())

    def _read_pcm16_le(self, buffer_data, position):
        value = buffer_data[position] | (buffer_data[position + 1] << 8)

        if value >= 32768:
            value -= 65536

        return value

    def _create_volume_table(self):
        """Build a 256-entry lookup table to scale the DAC output volume."""

        table = bytearray(256)

        for value in range(256):
            centered = value - 128
            adjusted = 128 + (centered * self._volumen_porcentaje // 100)

            if adjusted < 0:
                adjusted = 0
            elif adjusted > 255:
                adjusted = 255

            table[value] = adjusted

        return table

    def _get_or_initialize_dac(self):
        """Return a reusable DAC instance, creating it only once when possible."""

        if self._dac is not None:
            try:
                self._dac.write(128)
                return self._dac
            except Exception as exc:
                print("El DAC existente no respondió, se recreará:", exc)
                self._release_dac()

        last_error = None

        for attempt in range(1, 3):
            try:
                print("Inicializando DAC intento", attempt)
                self._dac = DAC(Pin(self._pin_audio))
                sleep_ms(20)
                self._dac.write(128)
                sleep_ms(20)
                return self._dac
            except Exception as exc:
                last_error = exc
                print("Error al inicializar DAC intento {}: {}".format(attempt, exc))
                self._release_dac()
                gc.collect()
                sleep_ms(200)

        raise RuntimeError(
            "No fue posible inicializar el DAC GPIO{}: {}".format(
                self._pin_audio,
                last_error,
            )
        )

    def _play_pcm_u8_8k(self, path, info):
        """Optimized path for WAV PCM unsigned 8-bit mono 8000 Hz."""

        if info["canales"] != 1:
            raise ValueError("Para reproducción U8 clara, el WAV debe ser mono.")

        if info["frecuencia"] != 8000:
            raise ValueError("Para la ruta U8 optimizada, el WAV debe estar a 8000 Hz.")

        period_us = 125
        volume_table = self._create_volume_table()
        audio_buffer = bytearray(1024)
        dac = self._get_or_initialize_dac()

        played_samples = 0
        next_tick = ticks_us()

        gc.collect()
        print("Memoria libre antes de reproducir:", gc.mem_free())
        print("Volumen digital:", self._volumen_porcentaje, "%")

        try:
            with open(path, "rb") as audio_file:
                audio_file.seek(info["posicion_datos"])
                remaining = info["tamano_datos"]

                gc.disable()

                while remaining > 0:
                    target_count = min(len(audio_buffer), remaining)
                    view = memoryview(audio_buffer)[:target_count]
                    bytes_read = audio_file.readinto(view)

                    if not bytes_read:
                        break

                    index = 0

                    if ticks_diff(next_tick, ticks_us()) < -(period_us * 4):
                        next_tick = ticks_us()

                    while index < bytes_read:
                        dac.write(volume_table[audio_buffer[index]])
                        next_tick = ticks_add(next_tick, period_us)

                        while ticks_diff(next_tick, ticks_us()) > 0:
                            pass

                        index += 1
                        played_samples += 1

                    remaining -= bytes_read
        finally:
            self._release_audio_resources(dac, audio_buffer, volume_table)

        if played_samples != info["tamano_datos"]:
            raise RuntimeError(
                "Audio incompleto: {} de {} muestras.".format(
                    played_samples,
                    info["tamano_datos"],
                )
            )

    def _play_pcm16_compatible(self, path, info):
        """Compatibility path for WAV PCM16 converting to U8 on the fly."""

        reduction_factor = (
            info["frecuencia"] + self._max_dac_rate - 1
        ) // self._max_dac_rate

        if reduction_factor < 1:
            reduction_factor = 1

        output_rate = info["frecuencia"] // reduction_factor
        period_us = 1000000 // output_rate
        bytes_per_frame = info["canales"] * 2
        total_frames = info["tamano_datos"] // bytes_per_frame

        print("  Factor de reducción:", reduction_factor)
        print("  Frecuencia DAC:", output_rate, "Hz")
        print("  Volumen digital:", self._volumen_porcentaje, "%")

        dac = self._get_or_initialize_dac()

        audio_buffer = bytearray(2048)
        volume_table = self._create_volume_table()

        processed_frames = 0
        global_index = 0
        next_tick = ticks_us()

        gc.collect()
        print("Memoria libre antes de reproducir:", gc.mem_free())

        try:
            with open(path, "rb") as audio_file:
                audio_file.seek(info["posicion_datos"])
                remaining_bytes = info["tamano_datos"]

                gc.disable()

                while remaining_bytes > 0:
                    bytes_read = audio_file.readinto(audio_buffer)

                    if not bytes_read:
                        break

                    valid_bytes = min(bytes_read, remaining_bytes)
                    valid_bytes -= valid_bytes % bytes_per_frame

                    if valid_bytes <= 0:
                        break

                    frames_in_block = valid_bytes // bytes_per_frame
                    frame = 0

                    if ticks_diff(next_tick, ticks_us()) < -(period_us * 4):
                        next_tick = ticks_us()

                    while frame < frames_in_block:
                        if global_index % reduction_factor == 0:
                            position = frame * bytes_per_frame
                            left = self._read_pcm16_le(audio_buffer, position)

                            if info["canales"] == 2:
                                right = self._read_pcm16_le(audio_buffer, position + 2)
                                sample = (left + right) // 2
                            else:
                                sample = left

                            sample_u8 = 128 + (sample >> 8)

                            if sample_u8 < 0:
                                sample_u8 = 0
                            elif sample_u8 > 255:
                                sample_u8 = 255

                            dac.write(volume_table[sample_u8])
                            next_tick = ticks_add(next_tick, period_us)

                            while ticks_diff(next_tick, ticks_us()) > 0:
                                pass

                        global_index += 1
                        frame += 1

                    processed_frames += frames_in_block
                    remaining_bytes -= valid_bytes
        finally:
            self._release_audio_resources(dac, audio_buffer, volume_table)

        if processed_frames < total_frames:
            raise RuntimeError(
                "El WAV no se reprodujo completo: {} de {} frames.".format(
                    processed_frames,
                    total_frames,
                )
            )

    def _release_audio_resources(self, dac, audio_buffer, volume_table):
        """Reset DAC output and free buffers even when playback fails."""

        gc.enable()

        try:
            dac.write(128)
        except Exception:
            pass

        sleep_ms(100)

        del audio_buffer
        del volume_table
        gc.collect()

    def _release_dac(self):
        """Fully release the DAC only when it becomes unusable."""

        if self._dac is None:
            return

        try:
            self._dac.write(128)
        except Exception:
            pass

        sleep_ms(50)

        try:
            self._dac.deinit()
        except (AttributeError, OSError):
            pass

        self._dac = None
        gc.collect()
