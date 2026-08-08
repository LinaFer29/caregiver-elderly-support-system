"""Audio processing services for the voice assistant STT flow."""

import io
import logging
import math
import time
import wave

import audioop
import numpy as np
from django.conf import settings
from django.core.exceptions import ValidationError

from voice.constants import DEFAULT_AUDIO_SAMPLE_RATE, VOICE_AUDIO_DEBUG_DEFAULT

logger = logging.getLogger(__name__)


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
        uploaded_file.seek(0)

        if not raw_audio:
            raise ValidationError("El archivo de audio está vacío.")

        self._debug("Bytes recibidos archivo=%s", len(raw_audio))

        if self._is_wav(raw_audio):
            return self._process_wav_bytes(raw_audio)

        source_sample_rate = sample_rate or self.target_sample_rate
        return self.process_pcm16_stream(raw_audio, sample_rate=source_sample_rate)

    def process_pcm16_stream(self, audio_bytes, sample_rate=None):
        """Process raw PCM16 bytes independently from their transport origin."""

        source_sample_rate = sample_rate or self.target_sample_rate
        step = "recibir bytes PCM16"

        try:
            self._debug("Inicio procesamiento PCM16 bytes=%s", len(audio_bytes))
            self._validate_pcm16_stream_not_empty(audio_bytes)

            step = "validar longitud del flujo PCM16"
            self._validate_pcm16_byte_length(audio_bytes)

            step = "validar sample rate"
            self._validate_sample_rate(source_sample_rate)

            step = "convertir flujo PCM16 a numpy.int16"
            int16_audio = self._convert_pcm16_bytes_to_int16(audio_bytes)

            step = "registrar estadisticas de int16"
            self._log_audio_stats(
                stage="pcm16-int16",
                audio_array=int16_audio,
                sample_rate=source_sample_rate,
            )

            step = "convertir numpy.int16 a numpy.float32"
            float32_audio = self._convert_int16_to_float32(int16_audio)

            step = "normalizar audio float32 al rango [-1, 1]"
            normalized_audio = self._normalize_float32_audio(float32_audio)

            step = "validar valores finitos del audio normalizado"
            self._validate_float32_audio(normalized_audio, stage="audio normalizado")

            step = "remuestrear audio normalizado"
            resample_start = time.perf_counter()
            output_audio, final_sample_rate = self._resample_float32_if_needed(
                normalized_audio,
                source_sample_rate=source_sample_rate,
            )
            resample_elapsed_ms = (time.perf_counter() - resample_start) * 1000

            step = "validar valores finitos despues del remuestreo"
            self._validate_float32_audio(
                output_audio,
                stage="audio remuestreado",
            )

            self._log_audio_stats(
                stage="pcm16-float32-final",
                audio_array=output_audio,
                sample_rate=final_sample_rate,
                resample_elapsed_ms=resample_elapsed_ms,
                source_sample_rate=source_sample_rate,
            )

            return output_audio
        except ValidationError:
            self._debug("Fallo en etapa=%s", step)
            raise
        except Exception as exc:
            self._debug("Excepcion inesperada en etapa=%s error=%s", step, exc)
            raise ValidationError(
                f"Ocurrio un error inesperado durante la etapa: {step}."
            ) from exc

    def _validate_file(self, uploaded_file):
        content_type = getattr(uploaded_file, "content_type", "") or ""
        extension = self._get_extension(uploaded_file.name)

        if content_type and content_type not in self.supported_content_types:
            if extension not in self.supported_extensions:
                raise ValidationError(
                    f"Formato de audio no soportado. content_type={content_type!r}, "
                    f"extension={extension or 'sin_extension'}."
                )

        if extension and extension not in self.supported_extensions:
            if content_type not in self.supported_content_types:
                raise ValidationError(
                    f"Formato de audio no soportado. extension={extension!r}, "
                    f"content_type={content_type or 'sin_content_type'}."
                )

    def _is_wav(self, raw_audio):
        return raw_audio[:4] == b"RIFF" and raw_audio[8:12] == b"WAVE"

    def _process_wav_bytes(self, raw_audio):
        pcm_bytes, source_sample_rate, sample_width = self._read_wav(raw_audio)

        if sample_width == 2:
            return self.process_pcm16_stream(pcm_bytes, sample_rate=source_sample_rate)

        float32_audio = self._convert_non_pcm16_bytes_to_float32(
            pcm_bytes,
            sample_width=sample_width,
        )
        self._validate_float32_audio(float32_audio, stage="audio WAV convertido")

        resample_start = time.perf_counter()
        output_audio, final_sample_rate = self._resample_float32_if_needed(
            float32_audio,
            source_sample_rate=source_sample_rate,
        )
        resample_elapsed_ms = (time.perf_counter() - resample_start) * 1000

        self._validate_float32_audio(output_audio, stage="audio WAV remuestreado")
        self._log_audio_stats(
            stage="wav-float32-final",
            audio_array=output_audio,
            sample_rate=final_sample_rate,
            resample_elapsed_ms=resample_elapsed_ms,
            source_sample_rate=source_sample_rate,
        )
        return output_audio

    def _read_wav(self, raw_audio):
        try:
            with wave.open(io.BytesIO(raw_audio), "rb") as wav_file:
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_count = wav_file.getnframes()
                pcm_bytes = wav_file.readframes(frame_count)
        except wave.Error as exc:
            raise ValidationError(
                f"No fue posible leer el archivo WAV: {exc}."
            ) from exc

        if sample_width not in self.supported_wav_widths:
            raise ValidationError(
                f"Profundidad de audio WAV no soportada: {sample_width} bytes por muestra."
            )

        if channels <= 0:
            raise ValidationError("El archivo WAV no contiene un numero de canales valido.")

        if channels > 1:
            try:
                pcm_bytes = audioop.tomono(pcm_bytes, sample_width, 0.5, 0.5)
            except audioop.error as exc:
                raise ValidationError(
                    f"No fue posible convertir el archivo WAV a mono: {exc}."
                ) from exc

        self._debug(
            "WAV leido sample_rate=%s channels=%s sample_width=%s frames=%s bytes=%s",
            sample_rate,
            channels,
            sample_width,
            frame_count,
            len(pcm_bytes),
        )
        return pcm_bytes, sample_rate, sample_width

    def _validate_pcm16_stream_not_empty(self, audio_bytes):
        if not audio_bytes:
            raise ValidationError("El flujo PCM16 está vacío.")

    def _validate_pcm16_byte_length(self, audio_bytes):
        byte_length = len(audio_bytes)
        if byte_length % 2 != 0:
            raise ValidationError(
                f"El tamaño del flujo PCM16 no es múltiplo de 2 bytes: {byte_length}."
            )

    def _validate_sample_rate(self, sample_rate):
        if sample_rate is None:
            raise ValidationError("No se recibió un sample_rate para procesar el audio.")

        if sample_rate <= 0:
            raise ValidationError(
                f"El sample_rate debe ser un entero positivo. Valor recibido: {sample_rate}."
            )

    def _convert_pcm16_bytes_to_int16(self, audio_bytes):
        try:
            return np.frombuffer(audio_bytes, dtype=np.int16)
        except ValueError as exc:
            raise ValidationError(
                f"No fue posible convertir el flujo PCM16 a numpy.int16: {exc}."
            ) from exc

    def _convert_int16_to_float32(self, int16_audio):
        return int16_audio.astype(np.float32)

    def _normalize_float32_audio(self, float32_audio):
        normalized_audio = float32_audio / 32768.0
        return normalized_audio.astype(np.float32, copy=False)

    def _validate_float32_audio(self, float32_audio, stage):
        if not isinstance(float32_audio, np.ndarray):
            raise ValidationError(
                f"La etapa {stage} no produjo un arreglo numpy valido."
            )

        if float32_audio.dtype != np.float32:
            raise ValidationError(
                f"La etapa {stage} produjo dtype {float32_audio.dtype}; se esperaba float32."
            )

        if np.isnan(float32_audio).any():
            raise ValidationError(f"La etapa {stage} produjo valores NaN.")

        if np.isinf(float32_audio).any():
            raise ValidationError(f"La etapa {stage} produjo valores infinitos.")

    def _resample_float32_if_needed(self, float32_audio, source_sample_rate):
        if source_sample_rate == self.target_sample_rate:
            self._debug(
                "Sin remuestreo sample_rate_inicial=%s sample_rate_final=%s",
                source_sample_rate,
                self.target_sample_rate,
            )
            return float32_audio, self.target_sample_rate

        if float32_audio.size == 0:
            raise ValidationError("No es posible remuestrear un audio sin muestras.")

        target_length = max(
            1,
            int(round(float32_audio.size * self.target_sample_rate / source_sample_rate)),
        )

        try:
            source_positions = np.linspace(
                0,
                float32_audio.size - 1,
                num=float32_audio.size,
                dtype=np.float64,
            )
            target_positions = np.linspace(
                0,
                float32_audio.size - 1,
                num=target_length,
                dtype=np.float64,
            )
            resampled_audio = np.interp(
                target_positions,
                source_positions,
                float32_audio.astype(np.float64),
            )
        except ValueError as exc:
            raise ValidationError(
                f"No fue posible remuestrear el audio desde {source_sample_rate} Hz "
                f"hasta {self.target_sample_rate} Hz: {exc}."
            ) from exc

        self._debug(
            "Remuestreo sample_rate_inicial=%s sample_rate_final=%s muestras_iniciales=%s muestras_finales=%s",
            source_sample_rate,
            self.target_sample_rate,
            float32_audio.size,
            target_length,
        )
        return resampled_audio.astype(np.float32), self.target_sample_rate

    def _convert_non_pcm16_bytes_to_float32(self, pcm_bytes, sample_width):
        if sample_width == 1:
            audio_array = np.frombuffer(pcm_bytes, dtype=np.uint8).astype(np.float32)
            return ((audio_array - 128.0) / 128.0).astype(np.float32, copy=False)

        if sample_width == 4:
            audio_array = np.frombuffer(pcm_bytes, dtype=np.int32).astype(np.float32)
            return (audio_array / 2147483648.0).astype(np.float32, copy=False)

        raise ValidationError(
            f"Profundidad de audio no soportada: {sample_width} bytes por muestra."
        )

    def convert_pcm16_to_float32(self, pcm_bytes):
        """Convert PCM16 little-endian mono bytes to normalized float32 audio."""

        int16_audio = self._convert_pcm16_bytes_to_int16(pcm_bytes)
        float32_audio = self._convert_int16_to_float32(int16_audio)
        normalized_audio = self._normalize_float32_audio(float32_audio)
        self._validate_float32_audio(normalized_audio, stage="convert_pcm16_to_float32")
        return normalized_audio

    def _log_audio_stats(
        self,
        stage,
        audio_array,
        sample_rate,
        resample_elapsed_ms=None,
        source_sample_rate=None,
    ):
        if not self._is_debug_enabled():
            return

        duration_seconds = 0.0
        if sample_rate and len(audio_array):
            duration_seconds = len(audio_array) / float(sample_rate)

        if len(audio_array):
            minimum = float(np.min(audio_array))
            maximum = float(np.max(audio_array))
            mean = float(np.mean(audio_array))
            rms = float(math.sqrt(float(np.mean(np.square(audio_array.astype(np.float64))))))
        else:
            minimum = maximum = mean = rms = 0.0

        self._debug(
            (
                "Audio stage=%s bytes=%s muestras=%s dtype=%s min=%s max=%s "
                "mean=%s rms=%s sample_rate_inicial=%s sample_rate_final=%s "
                "duracion_segundos=%s remuestreo_ms=%s"
            ),
            stage,
            getattr(audio_array, "nbytes", 0),
            len(audio_array),
            getattr(audio_array, "dtype", "desconocido"),
            minimum,
            maximum,
            mean,
            rms,
            source_sample_rate or sample_rate,
            sample_rate,
            duration_seconds,
            resample_elapsed_ms,
        )

    def _is_debug_enabled(self):
        return getattr(settings, "VOICE_AUDIO_DEBUG", VOICE_AUDIO_DEBUG_DEFAULT)

    def _debug(self, message, *args):
        if not self._is_debug_enabled():
            return

        formatted_message = message % args if args else message
        logger.info(formatted_message)
        print(formatted_message)

    def _get_extension(self, file_name):
        if "." not in file_name:
            return ""
        return f".{file_name.rsplit('.', 1)[-1].lower()}"
