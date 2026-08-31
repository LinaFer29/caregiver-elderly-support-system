"""Interpret spoken responses for assignment result updates."""

import logging
import re
import unicodedata
from threading import Lock

import numpy as np
from django.conf import settings

from voice.constants import (
    VOICE_RESPONSE_SEMANTIC_MIN_SCORE_MARGIN,
    VOICE_RESPONSE_SEMANTIC_MODEL_NAME,
    VOICE_RESPONSE_SEMANTIC_THRESHOLD,
    VOICE_RESPONSE_UNKNOWN_RESULT,
)

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None


class ResponseService:
    """Interpret STT transcriptions into assignment outcomes."""

    _semantic_model = None
    _semantic_catalog_cache = None
    _semantic_lock = Lock()

    unknown_result = VOICE_RESPONSE_UNKNOWN_RESULT
    semantic_model_name = VOICE_RESPONSE_SEMANTIC_MODEL_NAME
    semantic_threshold = VOICE_RESPONSE_SEMANTIC_THRESHOLD
    semantic_min_score_margin = VOICE_RESPONSE_SEMANTIC_MIN_SCORE_MARGIN

    COMPLETED_PATTERNS = (
        r"\b(si|sí)\b.*\b(ya\s+)?(hice|realice|realic[eé]|termine|termin[eé]|complete|complet[eé])\b",
        r"\bya\s+(hice|realice|realic[eé]|termine|termin[eé]|complete|complet[eé])\b",
        r"\bactividad\s+(realizada|terminada|completada)\b",
        r"\bya\s+quedo\b",
        r"\bla\s+actividad\s+ya\s+esta\s+(hecha|lista|realizada)\b",
    )
    MISSED_PATTERNS = (
        r"\bno\s+(hice|he\s+hecho|realice|realic[eé]|termine|termin[eé]|complete|complet[eé])\b",
        r"\bno\s+pude\b",
        r"\bno\s+alcance\b",
        r"\bactividad\s+no\s+(realizada|terminada|completada)\b",
        r"\bquedo\s+pendiente\b",
        r"\bincompleta\b",
    )
    semantic_catalog = {
        "completed": (
            "ya hice la actividad",
            "ya realice la actividad",
            "actividad completada",
            "ya termine",
            "ya termine la actividad",
            "la actividad ya esta hecha",
            "ya la hice",
            "eso ya lo hice",
            "ya quedo lista",
            "listo ya la hice",
            "ya cumpli con la actividad",
            "la actividad esta realizada",
            "activa completada",
            "esa ya quedo lista",
        ),
        "missed": (
            "no hice la actividad",
            "no la hice",
            "no pude hacerla",
            "no pude realizar la actividad",
            "no termine la actividad",
            "la actividad quedo incompleta",
            "no alcance a hacerla",
            "no realice la actividad",
            "todavia no la hago",
            "sigue pendiente",
        ),
    }

    def interpret_assignment_response(self, transcription):
        """Return a deterministic or semantic assignment result."""

        raw_transcription = (transcription or "").strip()
        normalized_transcription = self.normalize_text(transcription)

        rule_result = self._resolve_assignment_result_with_rules(
            normalized_transcription
        )
        if rule_result is not None:
            return {
                "transcription": raw_transcription,
                "normalized_transcription": normalized_transcription,
                "was_interpreted": True,
                "result": rule_result,
                "decision_source": "rules",
            }

        semantic_result = self._resolve_assignment_result_with_semantic_similarity(
            normalized_transcription
        )
        if semantic_result["result"] != self.unknown_result:
            return {
                "transcription": raw_transcription,
                "normalized_transcription": normalized_transcription,
                "was_interpreted": True,
                "result": semantic_result["result"],
                "decision_source": "semantic",
            }

        return {
            "transcription": raw_transcription,
            "normalized_transcription": normalized_transcription,
            "was_interpreted": False,
            "result": self.unknown_result,
            "decision_source": semantic_result["decision_source"],
        }

    def get_audio_path(self, file_name):
        """Return the absolute path for assistant-served audio files."""

        audio_root = settings.MEDIA_ROOT / "assistant_audio"
        return audio_root / file_name

    def normalize_text(self, text):
        """Normalize text to simplify deterministic and semantic matching."""

        compact_text = " ".join((text or "").strip().lower().split())
        normalized = unicodedata.normalize("NFD", compact_text)
        return "".join(
            char
            for char in normalized
            if unicodedata.category(char) != "Mn"
        )

    @classmethod
    def get_semantic_model(cls):
        """Return a singleton SentenceTransformer model instance."""

        if cls._semantic_model is None:
            with cls._semantic_lock:
                if cls._semantic_model is None:
                    if SentenceTransformer is None:
                        raise ImportError(
                            "No se pudo importar sentence-transformers. "
                            "Instala la dependencia `sentence-transformers`."
                        )
                    cls._semantic_model = SentenceTransformer(cls.semantic_model_name)
        return cls._semantic_model

    @classmethod
    def get_semantic_catalog_cache(cls):
        """Return normalized texts and embeddings for the semantic catalog."""

        if cls._semantic_catalog_cache is None:
            with cls._semantic_lock:
                if cls._semantic_catalog_cache is None:
                    model = cls.get_semantic_model()
                    normalized_catalog = {
                        label: [cls._normalize_static(text) for text in examples]
                        for label, examples in cls.semantic_catalog.items()
                    }
                    embeddings = {
                        label: model.encode(
                            examples,
                            convert_to_numpy=True,
                            normalize_embeddings=True,
                        )
                        for label, examples in normalized_catalog.items()
                    }
                    cls._semantic_catalog_cache = {
                        "texts": normalized_catalog,
                        "embeddings": embeddings,
                    }
        return cls._semantic_catalog_cache

    def _resolve_assignment_result_with_rules(self, normalized_transcription):
        for pattern in self.MISSED_PATTERNS:
            if re.search(pattern, normalized_transcription):
                return "missed"

        for pattern in self.COMPLETED_PATTERNS:
            if re.search(pattern, normalized_transcription):
                return "completed"

        return None

    def _resolve_assignment_result_with_semantic_similarity(
        self,
        normalized_transcription,
    ):
        if not normalized_transcription:
            return {
                "result": self.unknown_result,
                "decision_source": "semantic_empty",
                "completed_score": 0.0,
                "missed_score": 0.0,
            }

        try:
            scores = self._compute_semantic_scores(normalized_transcription)
        except Exception as exc:
            logger.warning(
                "Fallo la interpretacion semantica; se devuelve unknown. error=%s",
                exc,
            )
            return {
                "result": self.unknown_result,
                "decision_source": "semantic_unavailable",
                "completed_score": 0.0,
                "missed_score": 0.0,
            }

        completed_score = scores["completed"]
        missed_score = scores["missed"]
        best_label = "completed" if completed_score >= missed_score else "missed"
        best_score = scores[best_label]
        other_score = missed_score if best_label == "completed" else completed_score
        score_margin = best_score - other_score

        if best_score < self.semantic_threshold:
            return {
                "result": self.unknown_result,
                "decision_source": "semantic_below_threshold",
                "completed_score": completed_score,
                "missed_score": missed_score,
            }

        if score_margin < self.semantic_min_score_margin:
            return {
                "result": self.unknown_result,
                "decision_source": "semantic_low_margin",
                "completed_score": completed_score,
                "missed_score": missed_score,
            }

        return {
            "result": best_label,
            "decision_source": "semantic",
            "completed_score": completed_score,
            "missed_score": missed_score,
        }

    def _compute_semantic_scores(self, normalized_transcription):
        model = self.get_semantic_model()
        catalog_cache = self.get_semantic_catalog_cache()
        query_embedding = model.encode(
            [normalized_transcription],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )[0]

        scores = {}
        for label, embeddings in catalog_cache["embeddings"].items():
            similarities = np.dot(embeddings, query_embedding)
            scores[label] = float(np.max(similarities)) if len(similarities) else 0.0

        return scores

    @staticmethod
    def _normalize_static(text):
        compact_text = " ".join((text or "").strip().lower().split())
        normalized = unicodedata.normalize("NFD", compact_text)
        return "".join(
            char
            for char in normalized
            if unicodedata.category(char) != "Mn"
        )
