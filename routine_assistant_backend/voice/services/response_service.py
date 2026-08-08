"""Response resolution services for the voice assistant STT flow."""

import re
import unicodedata

from django.conf import settings


class ResponseService:
    """Map transcriptions to assistant intents and pre-recorded responses."""

    RESPONSE_CATALOG = {
        "activity_completed": {
            "response_text": "Actividad completada.",
            "audio_file": "actividad_completada.wav",
            "patterns": (
                r"\bya\s+(realice|realic[eé]|hice|termine|termin[eé]|complete|complet[eé])\s+la\s+actividad\b",
                r"\bactividad\s+(realizada|completada|terminada)\b",
                r"\bya\s+esta\s+lista\s+la\s+actividad\b",
                r"\btermine\b"
            ),
        },
        "next_activity": {
            "response_text": "La siguiente actividad es tomar agua.",
            "audio_file": "siguiente_actividad.wav",
            "patterns": (
                r"\bque\s+actividad\s+sigue\b",
                r"\bque\s+sigue\b",
                r"\bcual\s+es\s+la\s+siguiente\s+actividad\b",
                r"\bsiguiente\s+actividad\b",
            ),
        },
    }
    fallback_response = {
        "intent": None,
        "response_text": "No pude identificar la instruccion.",
        "audio_file": None,
    }

    def build_response(self, transcription):
        """Build the serialized response payload for a transcription."""

        normalized_transcription = self.normalize_text(transcription)
        response = self._resolve_intent(normalized_transcription)

        return {
            "transcription": normalized_transcription,
            "intent": response["intent"],
            "response_text": response["response_text"],
            "audio_file": response["audio_file"],
        }

    def get_audio_path(self, file_name):
        """Return the absolute path for a known assistant audio response."""

        audio_root = settings.MEDIA_ROOT / "assistant_audio"
        return audio_root / file_name

    def normalize_text(self, text):
        """Normalize text to simplify deterministic intent matching."""

        compact_text = " ".join((text or "").strip().lower().split())
        normalized = unicodedata.normalize("NFD", compact_text)
        return "".join(char for char in normalized if unicodedata.category(char) != "Mn")

    def _resolve_intent(self, normalized_transcription):
        for intent, config in self.RESPONSE_CATALOG.items():
            for pattern in config["patterns"]:
                if re.search(pattern, normalized_transcription):
                    return {
                        "intent": intent,
                        "response_text": config["response_text"],
                        "audio_file": config["audio_file"],
                    }

        return self.fallback_response
