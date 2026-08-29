"""Interpret spoken responses for assignment result updates."""

import re
import unicodedata

from django.conf import settings


class ResponseService:
    """Interpret STT transcriptions into deterministic assignment outcomes."""

    COMPLETED_PATTERNS = (
        r"\b(si|sí)\b.*\b(ya\s+)?(hice|realice|realic[eé]|termine|termin[eé]|complete|complet[eé])\b",
        r"\bya\s+(hice|realice|realic[eé]|termine|termin[eé]|complete|complet[eé])\b",
        r"\bactividad\s+(realizada|terminada|completada)\b",
        r"\bya\s+quedo\b",
    )
    MISSED_PATTERNS = (
        r"\bno\s+(hice|he\s+hecho|realice|realic[eé]|termine|termin[eé]|complete|complet[eé])\b",
        r"\bno\s+pude\b",
        r"\bno\s+alcance\b",
        r"\bactividad\s+no\s+(realizada|terminada|completada)\b",
        r"\bquedo\s+pendiente\b",
    )

    def interpret_assignment_response(self, transcription):
        """Return a deterministic assignment result from a transcription."""

        normalized_transcription = self.normalize_text(transcription)
        result = self._resolve_assignment_result(normalized_transcription)

        return {
            "transcription": (transcription or "").strip(),
            "normalized_transcription": normalized_transcription,
            "was_interpreted": result is not None,
            "result": result,
        }

    def get_audio_path(self, file_name):
        """Return the absolute path for assistant-served audio files."""

        audio_root = settings.MEDIA_ROOT / "assistant_audio"
        return audio_root / file_name

    def normalize_text(self, text):
        """Normalize text to simplify deterministic rule matching."""

        compact_text = " ".join((text or "").strip().lower().split())
        normalized = unicodedata.normalize("NFD", compact_text)
        return "".join(
            char
            for char in normalized
            if unicodedata.category(char) != "Mn"
        )

    def _resolve_assignment_result(self, normalized_transcription):
        for pattern in self.MISSED_PATTERNS:
            if re.search(pattern, normalized_transcription):
                return "missed"

        for pattern in self.COMPLETED_PATTERNS:
            if re.search(pattern, normalized_transcription):
                return "completed"

        return None
