"""Whisper transcription service for the voice assistant STT flow."""

import logging
import time
from threading import Lock

from django.conf import settings

from faster_whisper import WhisperModel

from voice.constants import VOICE_AUDIO_DEBUG_DEFAULT

logger = logging.getLogger(__name__)


class WhisperService:
    """Load Faster Whisper once and expose a reusable transcription API."""

    _model = None
    _model_lock = Lock()
    model_size = "base"
    compute_type = "int8"

    @classmethod
    def get_model(cls):
        """Return a singleton Faster Whisper model instance."""

        if cls._model is None:
            with cls._model_lock:
                if cls._model is None:
                    cls._model = WhisperModel(
                        cls.model_size,
                        device="cpu",
                        compute_type=cls.compute_type,
                    )
        return cls._model

    def transcribe(self, waveform):
        """Transcribe normalized mono audio and return plain text."""

        model = self.get_model()
        inference_start = time.perf_counter()
        segments, _info = model.transcribe(
            waveform,
            language="es",
            task="transcribe",
            beam_size=5,
            temperature=0,
            condition_on_previous_text=False,
        )
        inference_elapsed_ms = (time.perf_counter() - inference_start) * 1000
        transcription = " ".join(segment.text.strip() for segment in segments).strip()
        self._debug(
            "Whisper inferencia_ms=%s muestras=%s texto_len=%s",
            inference_elapsed_ms,
            len(waveform),
            len(transcription),
        )
        return transcription

    def _debug(self, message, *args):
        if not getattr(settings, "VOICE_AUDIO_DEBUG", VOICE_AUDIO_DEBUG_DEFAULT):
            return

        formatted_message = message % args if args else message
        logger.info(formatted_message)
        print(formatted_message)
