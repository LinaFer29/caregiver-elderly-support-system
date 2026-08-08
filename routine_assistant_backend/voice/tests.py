import io
import wave
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from voice.constants import DEFAULT_AUDIO_SAMPLE_RATE
from voice.services.audio_service import AudioProcessingService
from voice.services.response_service import ResponseService
from voice.services.voice_assistant_service import VoiceAssistantService


class ResponseServiceTests(TestCase):
    def setUp(self):
        self.service = ResponseService()

    def test_matches_activity_completed_intent_with_variation(self):
        response = self.service.build_response("Ya terminé la actividad")

        self.assertEqual(response["intent"], "activity_completed")
        self.assertEqual(response["audio_file"], "actividad_completada.wav")

    def test_matches_next_activity_intent_without_exact_phrase(self):
        response = self.service.build_response("Cual es la siguiente actividad")

        self.assertEqual(response["intent"], "next_activity")
        self.assertEqual(response["response_text"], "La siguiente actividad es tomar agua.")

    def test_returns_fallback_when_intent_is_unknown(self):
        response = self.service.build_response("Buenos dias")

        self.assertIsNone(response["intent"])
        self.assertIsNone(response["audio_file"])


class AudioProcessingServiceTests(TestCase):
    def setUp(self):
        self.service = AudioProcessingService()
        self.fixture_path = (
            Path(__file__).resolve().parent / "tests_fixtures" / "valid_pcm16_realistic.pcm"
        )

    def test_processes_pcm16_wav_into_normalized_float32(self):
        wav_bytes = self._build_wav(
            sample_rate=DEFAULT_AUDIO_SAMPLE_RATE,
            sample_values=[0, 16384, -16384],
        )
        uploaded_file = SimpleUploadedFile(
            "audio.wav",
            wav_bytes,
            content_type="audio/wav",
        )

        waveform = self.service.process(uploaded_file)

        self.assertEqual(waveform.dtype, np.float32)
        self.assertTrue(np.allclose(waveform[:3], np.array([0.0, 0.5, -0.5], dtype=np.float32)))

    def test_resamples_raw_pcm_when_sample_rate_differs_from_target(self):
        raw_pcm = np.array([0, 1000, -1000, 500], dtype=np.int16).tobytes()
        uploaded_file = SimpleUploadedFile(
            "audio.pcm",
            raw_pcm,
            content_type="audio/pcm",
        )

        waveform = self.service.process(uploaded_file, sample_rate=8000)

        self.assertEqual(waveform.dtype, np.float32)
        self.assertGreater(len(waveform), 0)

    def test_processes_pcm16_stream_into_normalized_float32(self):
        raw_pcm = np.array([0, 16384, -16384], dtype=np.int16).tobytes()

        waveform = self.service.process_pcm16_stream(
            raw_pcm,
            sample_rate=DEFAULT_AUDIO_SAMPLE_RATE,
        )

        self.assertEqual(waveform.dtype, np.float32)
        self.assertTrue(
            np.allclose(
                waveform[:3],
                np.array([0.0, 0.5, -0.5], dtype=np.float32),
            )
        )

    def test_rejects_invalid_pcm16_stream_with_odd_number_of_bytes(self):
        with self.assertRaisesMessage(
            Exception,
            "El tamaño del flujo PCM16 no es múltiplo de 2 bytes: 1.",
        ):
            self.service.process_pcm16_stream(
                b"\x01",
                sample_rate=DEFAULT_AUDIO_SAMPLE_RATE,
            )

    def test_processes_realistic_pcm16_fixture_without_validation_error(self):
        raw_pcm = self.fixture_path.read_bytes()

        waveform = self.service.process_pcm16_stream(
            raw_pcm,
            sample_rate=DEFAULT_AUDIO_SAMPLE_RATE,
        )

        self.assertEqual(waveform.dtype, np.float32)
        self.assertGreater(len(waveform), 0)

    def _build_wav(self, sample_rate, sample_values):
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(np.array(sample_values, dtype=np.int16).tobytes())
        return buffer.getvalue()


class VoiceAssistantSTTEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("voice.views.VoiceAssistantService")
    def test_returns_stt_response_payload(self, voice_assistant_service_cls):
        voice_assistant_service = Mock()
        voice_assistant_service.process_speech_command.return_value = {
            "transcription": "ya realice la actividad",
            "intent": "activity_completed",
            "response_text": "Actividad completada.",
            "audio_file": "actividad_completada.wav",
        }
        voice_assistant_service_cls.return_value = voice_assistant_service

        audio_file = SimpleUploadedFile(
            "audio.wav",
            b"fake-bytes",
            content_type="audio/wav",
        )

        response = self.client.post(
            "/api/voice/assistant/stt/",
            {"audio": audio_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"], "activity_completed")

    @patch("voice.views.VoiceAssistantService")
    def test_supports_root_assistant_stt_route(self, voice_assistant_service_cls):
        voice_assistant_service = Mock()
        voice_assistant_service.process_speech_command.return_value = {
            "transcription": "que sigue",
            "intent": "next_activity",
            "response_text": "La siguiente actividad es tomar agua.",
            "audio_file": "siguiente_actividad.wav",
        }
        voice_assistant_service_cls.return_value = voice_assistant_service

        audio_file = SimpleUploadedFile(
            "audio.wav",
            b"fake-bytes",
            content_type="audio/wav",
        )

        response = self.client.post(
            "/assistant/stt/",
            {"audio": audio_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"], "next_activity")

    @patch("voice.views.VoiceAssistantService")
    def test_accepts_octet_stream_audio(self, voice_assistant_service_cls):
        voice_assistant_service = Mock()
        voice_assistant_service.process_pcm16_command.return_value = {
            "transcription": "ya realice la actividad",
            "intent": "activity_completed",
            "response_text": "Actividad completada.",
            "audio_file": "actividad_completada.wav",
        }
        voice_assistant_service_cls.return_value = voice_assistant_service

        response = self.client.post(
            "/assistant/stt/",
            data=b"fake-wav-bytes",
            content_type="application/octet-stream",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"], "activity_completed")

        call_kwargs = voice_assistant_service.process_pcm16_command.call_args.kwargs
        self.assertEqual(call_kwargs["audio_bytes"], b"fake-wav-bytes")
        self.assertEqual(call_kwargs["sample_rate"], DEFAULT_AUDIO_SAMPLE_RATE)

    @patch("voice.views.VoiceAssistantService")
    def test_returns_400_for_empty_octet_stream(self, voice_assistant_service_cls):
        voice_assistant_service = Mock()
        voice_assistant_service.process_pcm16_command.side_effect = ValidationError(
            "El flujo PCM16 recibido está vacío."
        )
        voice_assistant_service_cls.return_value = voice_assistant_service

        response = self.client.post(
            "/assistant/stt/",
            data=b"",
            content_type="application/octet-stream",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], ["El flujo PCM16 recibido está vacío."])

    def test_rejects_path_traversal_attempts_in_audio_download(self):
        response = self.client.get("/api/voice/assistant/audio/../secret.wav/")

        self.assertEqual(response.status_code, 404)


class VoiceAssistantServiceTests(TestCase):
    def setUp(self):
        self.fixture_path = (
            Path(__file__).resolve().parent / "tests_fixtures" / "valid_pcm16_realistic.pcm"
        )

    def test_orchestrates_audio_whisper_and_response_services(self):
        audio_service = Mock()
        whisper_service = Mock()
        response_service = Mock()

        audio_service.process.return_value = np.array([0.0, 0.1], dtype=np.float32)
        whisper_service.transcribe.return_value = "ya hice la actividad"
        response_service.build_response.return_value = {
            "transcription": "ya hice la actividad",
            "intent": "activity_completed",
            "response_text": "Actividad completada.",
            "audio_file": "actividad_completada.wav",
        }

        service = VoiceAssistantService(
            audio_service=audio_service,
            whisper_service=whisper_service,
            response_service=response_service,
        )

        uploaded_file = SimpleUploadedFile("audio.wav", b"1234", content_type="audio/wav")
        result = service.process_speech_command(
            uploaded_file,
            sample_rate=DEFAULT_AUDIO_SAMPLE_RATE,
        )

        self.assertEqual(result["intent"], "activity_completed")
        audio_service.process.assert_called_once_with(
            uploaded_file,
            sample_rate=DEFAULT_AUDIO_SAMPLE_RATE,
        )
        whisper_service.transcribe.assert_called_once()
        response_service.build_response.assert_called_once_with("ya hice la actividad")

    def test_orchestrates_pcm16_audio_whisper_and_response_services(self):
        audio_service = Mock()
        whisper_service = Mock()
        response_service = Mock()

        audio_service.process_pcm16_stream.return_value = np.array([0.0, 0.1], dtype=np.float32)
        whisper_service.transcribe.return_value = "que sigue"
        response_service.build_response.return_value = {
            "transcription": "que sigue",
            "intent": "next_activity",
            "response_text": "La siguiente actividad es tomar agua.",
            "audio_file": "siguiente_actividad.wav",
        }

        service = VoiceAssistantService(
            audio_service=audio_service,
            whisper_service=whisper_service,
            response_service=response_service,
        )

        result = service.process_pcm16_command(
            b"1234",
            sample_rate=DEFAULT_AUDIO_SAMPLE_RATE,
        )

        self.assertEqual(result["intent"], "next_activity")
        audio_service.process_pcm16_stream.assert_called_once_with(
            b"1234",
            sample_rate=DEFAULT_AUDIO_SAMPLE_RATE,
        )
        whisper_service.transcribe.assert_called_once()
        response_service.build_response.assert_called_once_with("que sigue")

    def test_realistic_pcm16_fixture_reaches_whisper_without_validation_error(self):
        raw_pcm = self.fixture_path.read_bytes()
        whisper_service = Mock()
        response_service = Mock()

        whisper_service.transcribe.return_value = ""
        response_service.build_response.return_value = {
            "transcription": "",
            "intent": None,
            "response_text": "No pude identificar la instruccion.",
            "audio_file": None,
        }

        service = VoiceAssistantService(
            whisper_service=whisper_service,
            response_service=response_service,
        )

        result = service.process_pcm16_command(
            raw_pcm,
            sample_rate=DEFAULT_AUDIO_SAMPLE_RATE,
        )

        self.assertIsNone(result["intent"])
        whisper_service.transcribe.assert_called_once()
        response_service.build_response.assert_called_once_with("")
