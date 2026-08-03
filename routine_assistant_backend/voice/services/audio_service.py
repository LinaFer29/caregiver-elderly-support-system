"""Audio processing services for the voice assistant STT flow."""

import audioop
import io
import wave

import numpy as np
from django.core.exceptions import ValidationError

from voice.constants import DEFAULT_AUDIO_SAMPLE_RATE


class AudioProcessingService:
    """Validate and normalize uploaded audio for Faster Whisper.

    The production ESP32 contract for ``application/octet-stream`` is:
    - PCM signed 16 bits (int16)
    - little endian
    - mono
    - 16000 Hz
    - no WAV header
    - no compression

    The PCM16 conversion is intentionally separated from the transport layer so
    the same normalization path can later accept audio chunks for streaming.
    """

    target_sample_rate = DEFAULT_AUDIO_SAMPLE_RATE
    supported_wav_widths = {1, 2, 4}
    supported_content_types = {
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/vnd.wave",
        "audio/pcm",
        "audio/L16",
        "application/octet-stream",
    }
    supported_extensions = {".wav", ".pcm", ".raw"}

    def process(self, uploaded_file, sample_rate=None):
        """Return mono float32 audio normalized for Whisper from file input."""

        self._validate_file(uploaded_file)

        raw_audio = uploaded_file.read()
        if not raw_audio:
            raise ValidationError("El archivo de audio está vacío.")

        uploaded_file.seek(0)

        if self._is_wav(raw_audio):
            pcm_bytes, source_sample_rate, sample_width = self._read_wav(raw_audio)
        else:
            source_sample_rate = sample_rate or self.target_sample_rate
            pcm_bytes = raw_audio
            sample_width = 2
            self._validate_raw_pcm(pcm_bytes, source_sample_rate)

        pcm_bytes = self._resample_if_needed(
            pcm_bytes=pcm_bytes,
            sample_width=sample_width,
            source_sample_rate=source_sample_rate,
        )

        return self._pcm_to_float32(pcm_bytes, sample_width)

    def process_pcm16_stream(self, audio_bytes, sample_rate=None):
        """Process raw PCM16 bytes independently from their transport origin."""

        source_sample_rate = sample_rate or self.target_sample_rate
        self._validate_raw_pcm16_stream(audio_bytes, source_sample_rate)

        pcm_bytes = self._resample_if_needed(
            pcm_bytes=audio_bytes,
            sample_width=2,
            source_sample_rate=source_sample_rate,
        )

        return self.convert_pcm16_to_float32(pcm_bytes)

    def _validate_file(self, uploaded_file):
        content_type = getattr(uploaded_file, "content_type", "") or ""
        extension = self._get_extension(uploaded_file.name)

        if content_type and content_type not in self.supported_content_types:
            if extension not in self.supported_extensions:
                raise ValidationError("Formato de audio no soportado.")

        if extension and extension not in self.supported_extensions:
            if content_type not in self.supported_content_types:
                raise ValidationError("Formato de audio no soportado.")

    def _is_wav(self, raw_audio):
        return raw_audio[:4] == b"RIFF" and raw_audio[8:12] == b"WAVE"

    def _read_wav(self, raw_audio):
        try:
            with wave.open(io.BytesIO(raw_audio), "rb") as wav_file:
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_count = wav_file.getnframes()
                pcm_bytes = wav_file.readframes(frame_count)
        except wave.Error as exc:
            raise ValidationError("No fue posible leer el archivo WAV.") from exc

        if sample_width not in self.supported_wav_widths:
            raise ValidationError("Profundidad de audio WAV no soportada.")

        if channels > 1:
            pcm_bytes = audioop.tomono(pcm_bytes, sample_width, 0.5, 0.5)

        return pcm_bytes, sample_rate, sample_width

    def _validate_raw_pcm(self, pcm_bytes, sample_rate):
        print(f"Validating raw PCM: {len(pcm_bytes)} bytes, sample_rate={sample_rate}") 
        if sample_rate <= 0:
            raise ValidationError("El sample_rate debe ser un entero positivo.")

        if len(pcm_bytes) % 2 != 0:
            raise ValidationError("El audio PCM16 recibido no es válido.")

    def _validate_raw_pcm16_stream(self, audio_bytes, sample_rate):
        """Validate a complete PCM16 mono stream before decoding it."""

        if not audio_bytes:
            raise ValidationError("El flujo PCM16 recibido está vacío.")

        self._validate_raw_pcm(audio_bytes, sample_rate)

    def _resample_if_needed(self, pcm_bytes, sample_width, source_sample_rate):
        if source_sample_rate == self.target_sample_rate:
            return pcm_bytes

        try:
            converted_audio, _ = audioop.ratecv(
                pcm_bytes,
                sample_width,
                1,
                source_sample_rate,
                self.target_sample_rate,
                None,
            )
        except audioop.error as exc:
            raise ValidationError("No fue posible remuestrear el audio.") from exc

        return converted_audio

    def _pcm_to_float32(self, pcm_bytes, sample_width):
        if sample_width == 2:
            return self.convert_pcm16_to_float32(pcm_bytes)

        if sample_width == 1:
            audio_array = np.frombuffer(pcm_bytes, dtype=np.uint8).astype(np.float32)
            return (audio_array - 128.0) / 128.0

        if sample_width == 4:
            audio_array = np.frombuffer(pcm_bytes, dtype=np.int32).astype(np.float32)
            return audio_array / 2147483648.0

        raise ValidationError("Profundidad de audio no soportada.")

    def convert_pcm16_to_float32(self, pcm_bytes):
        """Convert PCM16 little-endian mono bytes to normalized float32 audio."""

        audio_array = np.frombuffer(pcm_bytes, dtype=np.int16)
        audio_array = audio_array.astype(np.float32)
        return audio_array / 32768.0

    def _get_extension(self, file_name):
        if "." not in file_name:
            return ""
        return f".{file_name.rsplit('.', 1)[-1].lower()}"
