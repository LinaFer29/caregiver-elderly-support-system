"""Text-to-speech services for the voice assistant module."""

import asyncio
import hashlib
import subprocess
import tempfile
import wave
from pathlib import Path

import edge_tts
from django.conf import settings
from django.core.exceptions import ValidationError

from voice.constants import (
    VOICE_TTS_FILENAME_PREFIX,
    VOICE_TTS_OUTPUT_CHANNELS,
    VOICE_TTS_OUTPUT_CODEC,
    VOICE_TTS_OUTPUT_SAMPLE_RATE,
    VOICE_TTS_OUTPUT_SAMPLE_WIDTH_BYTES,
    VOICE_TTS_VOICE,
)


class TTSService:
    """Generate speech audio files from text using Edge TTS."""

    voice = VOICE_TTS_VOICE
    output_sample_rate = VOICE_TTS_OUTPUT_SAMPLE_RATE
    output_channels = VOICE_TTS_OUTPUT_CHANNELS
    output_sample_width_bytes = VOICE_TTS_OUTPUT_SAMPLE_WIDTH_BYTES
    output_codec = VOICE_TTS_OUTPUT_CODEC
    filename_prefix = VOICE_TTS_FILENAME_PREFIX

    def generate_audio(self, text, identifier=None):
        """Generate a WAV file and return its filename and absolute path."""

        cleaned_text = " ".join((text or "").split())
        if not cleaned_text:
            raise ValidationError("No se recibió texto para generar el audio TTS.")

        output_path = self._build_output_path(cleaned_text, identifier=identifier)
        if output_path.exists():
            return {
                "audio_file": output_path.name,
                "audio_path": output_path,
            }

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "speech.mp3"
            self._synthesize_to_source_file(cleaned_text, source_path)
            self._convert_to_target_wav(source_path, output_path)

        self._validate_generated_wav(output_path)
        return {
            "audio_file": output_path.name,
            "audio_path": output_path,
        }

    def _build_output_path(self, text, identifier=None):
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
        file_stem = identifier or "general"
        file_name = f"{self.filename_prefix}_{file_stem}_{digest}.wav"
        return self._get_audio_root() / file_name

    def _get_audio_root(self):
        return settings.MEDIA_ROOT / "assistant_audio"

    def _synthesize_to_source_file(self, text, output_path):
        communicate = edge_tts.Communicate(text=text, voice=self.voice)

        try:
            asyncio.run(communicate.save(str(output_path)))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(communicate.save(str(output_path)))
            finally:
                loop.close()
        except Exception as exc:
            raise ValidationError(
                f"No fue posible generar el audio TTS con edge-tts: {exc}."
            ) from exc

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise ValidationError("edge-tts no generó un archivo de audio válido.")

    def _convert_to_target_wav(self, source_path, output_path):
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-ac",
            str(self.output_channels),
            "-ar",
            str(self.output_sample_rate),
            "-acodec",
            self.output_codec,
            str(output_path),
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ValidationError(
                "No se encontró ffmpeg para convertir el audio TTS a WAV."
            ) from exc

        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ValidationError(
                "No fue posible convertir el audio TTS a WAV 8000 Hz. "
                f"Detalle ffmpeg: {detail}."
            )

    def _validate_generated_wav(self, output_path):
        try:
            with wave.open(str(output_path), "rb") as wav_file:
                channels = wav_file.getnchannels()
                sample_rate = wav_file.getframerate()
                sample_width = wav_file.getsampwidth()
                compression_type = wav_file.getcomptype()
        except wave.Error as exc:
            raise ValidationError(
                f"El archivo TTS generado no es un WAV válido: {exc}."
            ) from exc

        if channels != self.output_channels:
            raise ValidationError(
                f"El audio TTS generado no es mono. Canales detectados: {channels}."
            )

        if sample_rate != self.output_sample_rate:
            raise ValidationError(
                f"El audio TTS generado no tiene {self.output_sample_rate} Hz. "
                f"Frecuencia detectada: {sample_rate} Hz."
            )

        if sample_width != self.output_sample_width_bytes:
            raise ValidationError("El audio TTS generado no es PCM de 16 bits.")

        if compression_type != "NONE":
            raise ValidationError(
                "El audio TTS generado no está en PCM sin compresión."
            )
