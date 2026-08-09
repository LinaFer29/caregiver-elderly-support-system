import io
import wave
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from activities.models import Activity, Category
from routines.models import Assignment
from users.models import Caregiver, Device, Elderly
from voice.constants import (
    DEFAULT_AUDIO_SAMPLE_RATE,
    VOICE_TTS_OUTPUT_SAMPLE_RATE,
)
from voice.services.audio_service import AudioProcessingService
from voice.services.response_service import ResponseService
from voice.services.tts_service import TTSService
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
        self.assertEqual(
            response["response_text"],
            "La siguiente actividad es tomar agua.",
        )

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
        self.assertTrue(
            np.allclose(
                waveform[:3],
                np.array([0.0, 0.5, -0.5], dtype=np.float32),
            )
        )

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
            "El flujo PCM16 está vacío."
        )
        voice_assistant_service_cls.return_value = voice_assistant_service

        response = self.client.post(
            "/assistant/stt/",
            data=b"",
            content_type="application/octet-stream",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], ["El flujo PCM16 está vacío."])

    def test_rejects_path_traversal_attempts_in_audio_download(self):
        response = self.client.get("/api/voice/assistant/audio/../secret.wav/")

        self.assertEqual(response.status_code, 404)


@override_settings(MEDIA_ROOT=Path(__file__).resolve().parent / "test_media")
class TTSServiceTests(TestCase):
    def setUp(self):
        self.service = TTSService()
        self.media_root = Path(settings.MEDIA_ROOT)
        self.media_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.media_root.exists():
            for path in sorted(self.media_root.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()

    def test_converts_generated_audio_to_wav_pcm_mono_8000hz(self):
        with patch.object(
            self.service,
            "_synthesize_to_source_file",
            side_effect=self._write_source_wav,
        ):
            result = self.service.generate_audio(
                "Hola, este es un recordatorio de prueba.",
                identifier="simple",
            )

        self.assertTrue(result["audio_path"].exists())

        with wave.open(str(result["audio_path"]), "rb") as wav_file:
            self.assertEqual(wav_file.getframerate(), VOICE_TTS_OUTPUT_SAMPLE_RATE)
            self.assertEqual(wav_file.getnchannels(), 1)
            self.assertEqual(wav_file.getsampwidth(), 2)
            self.assertEqual(wav_file.getcomptype(), "NONE")

    def _write_source_wav(self, _text, output_path):
        sample_values = np.array([0, 2000, -2000, 1000] * 4000, dtype=np.int16)
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24000)
            wav_file.writeframes(sample_values.tobytes())


@override_settings(MEDIA_ROOT=Path(__file__).resolve().parent / "test_media")
class VoiceAssistantServiceTests(TestCase):
    def setUp(self):
        self.fixture_path = (
            Path(__file__).resolve().parent / "tests_fixtures" / "valid_pcm16_realistic.pcm"
        )
        self.media_root = Path(settings.MEDIA_ROOT)
        self.media_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.media_root.exists():
            for path in sorted(self.media_root.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()

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

    @patch("voice.services.voice_assistant_service.TTSService.generate_audio")
    def test_reuses_real_reminder_flow_with_additional_instructions_for_tts(
        self,
        generate_audio_mock,
    ):
        assignment = self._create_due_assignment(
            title="Tomar medicación",
            description="Tomar la medicina asignada.",
            additional_instructions="Tomar Losartán 50mg después del desayuno.",
            mac_address="AA:BB:CC:DD:EE:01",
        )
        generate_audio_mock.return_value = {
            "audio_file": "tts_assignment_1_demo.wav",
            "audio_path": self.media_root / "assistant_audio" / "tts_assignment_1_demo.wav",
        }

        service = VoiceAssistantService()
        reminders = service.get_due_reminders("AA:BB:CC:DD:EE:01")

        self.assertEqual(len(reminders), 1)
        self.assertEqual(reminders[0]["assignment_id"], assignment.id)
        self.assertEqual(reminders[0]["activity"], "Tomar medicación")
        self.assertEqual(
            reminders[0]["message"],
            "Es hora de Tomar medicación. Tomar Losartán 50mg después del desayuno.",
        )
        self.assertEqual(reminders[0]["audio_file"], "tts_assignment_1_demo.wav")
        spoken_text = generate_audio_mock.call_args.kwargs["text"]
        self.assertIn("Hola, es momento de realizar una actividad.", spoken_text)
        self.assertIn("Es hora de Tomar medicación.", spoken_text)
        self.assertIn("Tomar Losartán 50mg después del desayuno.", spoken_text)

    @patch("voice.services.voice_assistant_service.TTSService.generate_audio")
    def test_reuses_real_reminder_flow_without_additional_instructions_for_tts(
        self,
        generate_audio_mock,
    ):
        assignment = self._create_due_assignment(
            title="Tomar agua",
            description="Tomar un vaso de agua.",
            additional_instructions="",
            mac_address="AA:BB:CC:DD:EE:02",
        )
        generate_audio_mock.return_value = {
            "audio_file": "tts_assignment_2_demo.wav",
            "audio_path": self.media_root / "assistant_audio" / "tts_assignment_2_demo.wav",
        }

        service = VoiceAssistantService()
        reminders = service.get_due_reminders("AA:BB:CC:DD:EE:02")

        self.assertEqual(len(reminders), 1)
        self.assertEqual(reminders[0]["assignment_id"], assignment.id)
        self.assertEqual(
            reminders[0]["message"],
            "Es hora de Tomar agua. Tomar un vaso de agua.",
        )
        spoken_text = generate_audio_mock.call_args.kwargs["text"]
        self.assertIn("Tomar un vaso de agua.", spoken_text)
        self.assertEqual(reminders[0]["audio_file"], "tts_assignment_2_demo.wav")

    def _create_due_assignment(self, title, description, additional_instructions, mac_address):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username=f"user_{mac_address.replace(':', '')}",
            password="test1234",
            role="caregiver",
        )
        caregiver = Caregiver.objects.create(user=user, caregiver_type="formal")
        elderly = Elderly.objects.create(
            first_name="Ana",
            last_name="Pérez",
            age=78,
            caregiver=caregiver,
            relationship_to_caregiver="Hija",
            dependency_level="media",
            underlying_conditions="Hipertensión",
        )
        Device.objects.create(
            name="ESP32 Voice",
            serial_number=f"SER-{mac_address.replace(':', '')}",
            mac_address=mac_address,
            model="ESP32",
            status="assigned",
            elderly=elderly,
        )
        category = Category.objects.create(name=f"Categoria {mac_address}")
        activity = Activity.objects.create(
            title=title,
            description=description,
            category=category,
        )

        now = timezone.localtime()
        return Assignment.objects.create(
            elderly=elderly,
            activity=activity,
            date=now.date(),
            notification_time=(now - timedelta(minutes=1)).time(),
            additional_instructions=additional_instructions,
            status="pending",
        )
