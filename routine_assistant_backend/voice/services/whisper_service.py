"""Whisper transcription service for the voice assistant STT flow."""

from threading import Lock

from faster_whisper import WhisperModel


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
        segments, _info = model.transcribe(
            waveform,
            language=None,
            task="transcribe",
            beam_size=1,
        )
        transcription = " ".join(segment.text.strip() for segment in segments).strip()
        return transcription
