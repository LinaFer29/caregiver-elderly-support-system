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
    VOICE_RESPONSE_UNKNOWN_RESULT,
    VOICE_TTS_OUTPUT_SAMPLE_RATE,
)
from voice.services.assignment_response_service import AssignmentResponseService
from voice.services.audio_service import AudioProcessingService
from voice.services.mqtt_service import VoiceMQTTPublisherService
from voice.services.reminder_service import ReminderService
from voice.services.response_service import ResponseService
from voice.tasks import dispatch_due_assignments
from voice.services.tts_service import TTSService
from voice.services.voice_assistant_service import VoiceAssistantService


class ResponseServiceTests(TestCase):
    def setUp(self):
        self.service = ResponseService()

    def test_interprets_completed_response_with_variation(self):
        response = self.service.interpret_assignment_response(
            "Sí, ya terminé la actividad"
        )

        self.assertEqual(response["result"], "completed")
        self.assertTrue(response["was_interpreted"])

    def test_interprets_missed_response(self):
        response = self.service.interpret_assignment_response("No pude hacerla")

        self.assertEqual(response["result"], "missed")
        self.assertTrue(response["was_interpreted"])

    @patch.object(
        ResponseService,
        "_compute_semantic_scores",
        return_value={"completed": 0.93, "missed": 0.21},
    )
    def test_interprets_semantic_completed_variation(self, _scores_mock):
        response = self.service.interpret_assignment_response("Eso ya lo hice")

        self.assertEqual(response["result"], "completed")
        self.assertEqual(response["decision_source"], "semantic")

    @patch.object(
        ResponseService,
        "_compute_semantic_scores",
        return_value={"completed": 0.92, "missed": 0.20},
    )
    def test_interprets_whisper_typo_as_completed_semantically(self, _scores_mock):
        response = self.service.interpret_assignment_response("Activa completada")

        self.assertEqual(response["result"], "completed")
        self.assertTrue(response["was_interpreted"])

    @patch.object(
        ResponseService,
        "_compute_semantic_scores",
        return_value={"completed": 0.22, "missed": 0.89},
    )
    def test_interprets_semantic_missed_variation(self, _scores_mock):
        response = self.service.interpret_assignment_response("Todavia no la hago")

        self.assertEqual(response["result"], "missed")
        self.assertEqual(response["decision_source"], "semantic")

    @patch.object(
        ResponseService,
        "_compute_semantic_scores",
        return_value={"completed": 0.40, "missed": 0.33},
    )
    def test_returns_unknown_when_scores_do_not_reach_threshold(self, _scores_mock):
        response = self.service.interpret_assignment_response("Que actividad")

        self.assertEqual(response["result"], VOICE_RESPONSE_UNKNOWN_RESULT)
        self.assertFalse(response["was_interpreted"])

    @patch.object(
        ResponseService,
        "_compute_semantic_scores",
        return_value={"completed": 0.78, "missed": 0.76},
    )
    def test_returns_unknown_when_score_margin_is_too_small(self, _scores_mock):
        response = self.service.interpret_assignment_response(
            "Creo que si pero no estoy segura"
        )

        self.assertEqual(response["result"], VOICE_RESPONSE_UNKNOWN_RESULT)
        self.assertFalse(response["was_interpreted"])
        self.assertEqual(response["decision_source"], "semantic_low_margin")

    @patch.object(
        ResponseService,
        "_compute_semantic_scores",
        return_value={"completed": 0.24, "missed": 0.21},
    )
    def test_returns_unknown_for_ambiguous_response(self, _scores_mock):
        response = self.service.interpret_assignment_response("Buenos dias")

        self.assertEqual(response["result"], VOICE_RESPONSE_UNKNOWN_RESULT)
        self.assertFalse(response["was_interpreted"])


class AssignmentResponseServiceTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.service = AssignmentResponseService()
        self.assignment = self._create_assignment(mac_address="AA:BB:CC:DD:EE:90")

    def test_marks_assignment_as_completed(self):
        result = self.service.register_response(
            mac_address="AA:BB:CC:DD:EE:90",
            assignment_id=self.assignment.id,
            transcription="Sí, ya la hice",
            result="completed",
        )

        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, "completed")
        self.assertEqual(self.assignment.user_response, "Sí, ya la hice")
        self.assertTrue(result["assignment_updated"])

    def test_marks_assignment_as_missed(self):
        result = self.service.register_response(
            mac_address="AA:BB:CC:DD:EE:90",
            assignment_id=self.assignment.id,
            transcription="No pude hacerla",
            result="missed",
        )

        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, "missed")
        self.assertTrue(result["assignment_updated"])

    def test_keeps_assignment_pending_for_ambiguous_response(self):
        result = self.service.register_response(
            mac_address="AA:BB:CC:DD:EE:90",
            assignment_id=self.assignment.id,
            transcription="No recuerdo",
            result=VOICE_RESPONSE_UNKNOWN_RESULT,
        )

        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, "pending")
        self.assertEqual(self.assignment.user_response, "No recuerdo")
        self.assertFalse(result["assignment_updated"])

    def test_rejects_missing_device(self):
        with self.assertRaisesMessage(
            ValidationError,
            "No existe un dispositivo asociado a la mac_address recibida.",
        ):
            self.service.register_response(
                mac_address="FF:FF:FF:FF:FF:FF",
                assignment_id=self.assignment.id,
                transcription="Sí",
                result="completed",
            )

    def test_rejects_device_without_elderly(self):
        user = self.user_model.objects.create_user(
            username="device_without_elderly",
            password="test1234",
            role="caregiver",
        )
        Device.objects.create(
            name="ESP32 libre",
            serial_number="SER-FREE-1",
            mac_address="AA:BB:CC:DD:EE:91",
            model="ESP32",
            status="available",
            elderly=None,
        )

        with self.assertRaisesMessage(
            ValidationError,
            "El dispositivo recibido no tiene un adulto mayor asociado.",
        ):
            self.service.register_response(
                mac_address="AA:BB:CC:DD:EE:91",
                assignment_id=self.assignment.id,
                transcription="Sí",
                result="completed",
            )

    def test_rejects_assignment_from_other_device(self):
        other_assignment = self._create_assignment(mac_address="AA:BB:CC:DD:EE:92")

        with self.assertRaisesMessage(
            ValidationError,
            "La assignment no corresponde al adulto mayor asociado al dispositivo.",
        ):
            self.service.register_response(
                mac_address="AA:BB:CC:DD:EE:90",
                assignment_id=other_assignment.id,
                transcription="Sí",
                result="completed",
            )

    def test_rejects_missing_assignment(self):
        with self.assertRaisesMessage(
            ValidationError,
            "No existe la assignment indicada.",
        ):
            self.service.register_response(
                mac_address="AA:BB:CC:DD:EE:90",
                assignment_id=999999,
                transcription="Sí",
                result="completed",
            )

    def _create_assignment(self, mac_address):
        user = self.user_model.objects.create_user(
            username=mac_address.replace(":", "").lower(),
            password="test1234",
            role="caregiver",
        )
        caregiver = Caregiver.objects.create(user=user, caregiver_type="formal")
        elderly = Elderly.objects.create(
            first_name="Rosa",
            last_name="Lopez",
            age=81,
            caregiver=caregiver,
            relationship_to_caregiver="Hija",
            dependency_level="media",
            underlying_conditions="Hipertension",
        )
        Device.objects.create(
            name="ESP32 response",
            serial_number="SER-" + mac_address.replace(":", ""),
            mac_address=mac_address,
            model="ESP32",
            status="assigned",
            elderly=elderly,
        )
        category = Category.objects.create(name="Categoria " + mac_address.replace(":", ""))
        activity = Activity.objects.create(
            title="Tomar medicamento",
            description="Tomar el medicamento asignado.",
            category=category,
        )
        return Assignment.objects.create(
            elderly=elderly,
            activity=activity,
            date=timezone.localdate(),
            notification_time=timezone.localtime().time().replace(second=0, microsecond=0),
            additional_instructions="",
            status="pending",
        )


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
        voice_assistant_service.process_assignment_response_file.return_value = {
            "audio_received": True,
            "stt_success": True,
            "transcription": "si ya hice la actividad",
            "normalized_transcription": "si ya hice la actividad",
            "was_interpreted": True,
            "result": "completed",
            "assignment_id": 15,
            "assignment_status": "completed",
            "assignment_updated": True,
        }
        voice_assistant_service_cls.return_value = voice_assistant_service

        audio_file = SimpleUploadedFile(
            "audio.wav",
            b"fake-bytes",
            content_type="audio/wav",
        )

        response = self.client.post(
            "/api/voice/assistant/stt/",
            {
                "audio": audio_file,
                "assignment_id": 15,
                "mac_address": "AA:BB:CC:DD:EE:01",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "completed")

    @patch("voice.views.VoiceAssistantService")
    def test_supports_root_assistant_stt_route(self, voice_assistant_service_cls):
        voice_assistant_service = Mock()
        voice_assistant_service.process_assignment_response_file.return_value = {
            "audio_received": True,
            "stt_success": True,
            "transcription": "no pude hacerla",
            "normalized_transcription": "no pude hacerla",
            "was_interpreted": True,
            "result": "missed",
            "assignment_id": 22,
            "assignment_status": "missed",
            "assignment_updated": True,
        }
        voice_assistant_service_cls.return_value = voice_assistant_service

        audio_file = SimpleUploadedFile(
            "audio.wav",
            b"fake-bytes",
            content_type="audio/wav",
        )

        response = self.client.post(
            "/assistant/stt/",
            {
                "audio": audio_file,
                "assignment_id": 22,
                "mac_address": "AA:BB:CC:DD:EE:02",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "missed")

    @patch("voice.views.VoiceAssistantService")
    def test_accepts_octet_stream_audio(self, voice_assistant_service_cls):
        voice_assistant_service = Mock()
        voice_assistant_service.process_assignment_response_stream.return_value = {
            "audio_received": True,
            "stt_success": True,
            "transcription": "ya realice la actividad",
            "normalized_transcription": "ya realice la actividad",
            "was_interpreted": True,
            "result": "completed",
            "assignment_id": 12,
            "assignment_status": "completed",
            "assignment_updated": True,
        }
        voice_assistant_service_cls.return_value = voice_assistant_service

        response = self.client.post(
            "/assistant/stt/?assignment_id=12&mac_address=AA:BB:CC:DD:EE:03",
            data=b"fake-wav-bytes",
            content_type="application/octet-stream",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "completed")

        call_kwargs = (
            voice_assistant_service.process_assignment_response_stream.call_args.kwargs
        )
        self.assertEqual(call_kwargs["audio_bytes"], b"fake-wav-bytes")
        self.assertEqual(call_kwargs["sample_rate"], DEFAULT_AUDIO_SAMPLE_RATE)
        self.assertEqual(call_kwargs["assignment_id"], 12)
        self.assertEqual(call_kwargs["mac_address"], "AA:BB:CC:DD:EE:03")

    @patch("voice.views.VoiceAssistantService")
    def test_returns_400_for_empty_octet_stream(self, voice_assistant_service_cls):
        voice_assistant_service = Mock()
        voice_assistant_service.process_assignment_response_stream.side_effect = ValidationError(
            "El flujo PCM16 está vacío."
        )
        voice_assistant_service_cls.return_value = voice_assistant_service

        response = self.client.post(
            "/assistant/stt/?assignment_id=1&mac_address=AA:BB:CC:DD:EE:04",
            data=b"",
            content_type="application/octet-stream",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], ["El flujo PCM16 está vacío."])

    def test_returns_400_for_missing_assignment_metadata(self):
        response = self.client.post(
            "/assistant/stt/",
            data=b"fake-pcm",
            content_type="application/octet-stream",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("assignment_id", response.json()["detail"])

    def test_rejects_path_traversal_attempts_in_audio_download(self):
        response = self.client.get("/api/voice/assistant/audio/../secret.wav/")

        self.assertEqual(response.status_code, 404)


class VoiceMQTTPublisherServiceTests(TestCase):
    def setUp(self):
        self.service = VoiceMQTTPublisherService()

    def test_builds_device_id_from_mac_address(self):
        self.assertEqual(
            self.service.build_device_id("B4:8A:0A:57:7C:E8"),
            "b48a0a577ce8",
        )

    def test_builds_expected_topic(self):
        topic = self.service.build_topic("b48a0a577ce8")

        self.assertEqual(topic, "device/b48a0a577ce8/audio")

    def test_builds_activity_payload(self):
        activity = Activity(id=1, title="Tomar medicamento", description="Tomar el medicamento.")

        payload = self.service.build_activity_payload(activity)

        self.assertEqual(
            payload,
            {
                "type": "activity",
                "activity_id": 1,
                "title": "Tomar medicamento",
                "description": "Tomar el medicamento.",
            },
        )

    def test_builds_reminder_payload_from_existing_http_contract(self):
        payload = self.service.build_reminder_payload(
            {
                "assignment_id": 9,
                "elderly_id": 3,
                "activity": "Tomar medicamento",
                "message": "Es hora de Tomar medicamento. Tomar el medicamento de la mañana.",
                "scheduled_time": timezone.datetime(
                    2026,
                    8,
                    9,
                    8,
                    0,
                    0,
                ).time(),
                "audio_file": "tts_assignment_9_abcd1234.wav",
            }
        )

        self.assertEqual(
            payload,
            {
                "type": "activity",
                "assignment_id": 9,
                "elderly_id": 3,
                "activity": "Tomar medicamento",
                "message": "Es hora de Tomar medicamento. Tomar el medicamento de la mañana.",
                "scheduled_time": "08:00:00",
                "audio_file": "tts_assignment_9_abcd1234.wav",
            },
        )


class ReminderDispatchServiceTests(TestCase):
    def setUp(self):
        self.service = ReminderService()
        self.user_model = get_user_model()
        self.category = Category.objects.create(name="Categoria recordatorios")
        self.sequence = 0

    def test_detects_pending_assignment_scheduled_in_current_minute(self):
        reference_datetime = timezone.localtime().replace(second=30, microsecond=0)
        assignment = self._create_assignment(
            date=reference_datetime.date(),
            notification_time=reference_datetime.time().replace(second=0, microsecond=0),
            status="pending",
            mac_address="B4:8A:0A:57:7C:E8",
        )

        assignments = list(
            self.service.get_assignments_due_for_dispatch(
                reference_datetime=reference_datetime,
            )
        )

        self.assertEqual(assignments, [assignment])

    def test_ignores_assignments_from_other_dates(self):
        reference_datetime = timezone.localtime().replace(second=15, microsecond=0)
        self._create_assignment(
            date=reference_datetime.date() + timedelta(days=1),
            notification_time=reference_datetime.time().replace(second=0, microsecond=0),
            status="pending",
            mac_address="AA:BB:CC:DD:EE:10",
        )

        assignments = list(
            self.service.get_assignments_due_for_dispatch(
                reference_datetime=reference_datetime,
            )
        )

        self.assertEqual(assignments, [])

    def test_ignores_assignments_with_non_pending_status(self):
        reference_datetime = timezone.localtime().replace(second=45, microsecond=0)
        self._create_assignment(
            date=reference_datetime.date(),
            notification_time=reference_datetime.time().replace(second=0, microsecond=0),
            status="completed",
            mac_address="AA:BB:CC:DD:EE:11",
        )

        assignments = list(
            self.service.get_assignments_due_for_dispatch(
                reference_datetime=reference_datetime,
            )
        )

        self.assertEqual(assignments, [])

    def test_resolves_device_from_assignment_elderly_relationship(self):
        assignment = self._create_assignment(
            date=timezone.localdate(),
            notification_time=timezone.localtime().time().replace(second=0, microsecond=0),
            status="pending",
            mac_address="AA:BB:CC:DD:EE:12",
        )

        device = self.service.get_device_for_elderly(assignment.elderly)

        self.assertIsNotNone(device)
        self.assertEqual(device.elderly_id, assignment.elderly_id)
        self.assertEqual(device.mac_address, "AA:BB:CC:DD:EE:12")

    @patch("voice.tasks.VoiceAssistantService.build_due_reminder_payload")
    @patch("voice.tasks.VoiceMQTTPublisherService")
    def test_dispatch_task_publishes_due_assignment_using_device_mac(
        self,
        mqtt_service_cls,
        build_due_reminder_payload_mock,
    ):
        reference_datetime = timezone.localtime().replace(second=0, microsecond=0)
        assignment = self._create_assignment(
            date=reference_datetime.date(),
            notification_time=reference_datetime.time(),
            status="pending",
            mac_address="B4:8A:0A:57:7C:E8",
        )
        mqtt_service = mqtt_service_cls.return_value
        build_due_reminder_payload_mock.return_value = {
            "assignment_id": assignment.id,
            "elderly_id": assignment.elderly_id,
            "activity": assignment.activity.title,
            "message": "Es hora de la actividad.",
            "scheduled_time": assignment.notification_time,
            "audio_file": "tts_assignment_demo.wav",
        }

        published_count = dispatch_due_assignments()

        self.assertEqual(published_count, 1)
        build_due_reminder_payload_mock.assert_called_once_with(assignment)
        mqtt_service.publish_reminder.assert_called_once_with(
            "B4:8A:0A:57:7C:E8",
            {
                "assignment_id": assignment.id,
                "elderly_id": assignment.elderly_id,
                "activity": assignment.activity.title,
                "message": "Es hora de la actividad.",
                "scheduled_time": assignment.notification_time,
                "audio_file": "tts_assignment_demo.wav",
            },
        )
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, "pending")

    @patch("voice.tasks.VoiceMQTTPublisherService")
    def test_dispatch_task_skips_due_assignment_without_device(self, mqtt_service_cls):
        reference_datetime = timezone.localtime().replace(second=0, microsecond=0)
        self._create_assignment(
            date=reference_datetime.date(),
            notification_time=reference_datetime.time(),
            status="pending",
            mac_address=None,
            create_device=False,
        )

        published_count = dispatch_due_assignments()

        self.assertEqual(published_count, 0)
        mqtt_service_cls.return_value.publish_reminder.assert_not_called()

    def _create_assignment(
        self,
        date,
        notification_time,
        status,
        mac_address,
        create_device=True,
    ):
        self.sequence += 1
        user = self.user_model.objects.create_user(
            username=f"dispatch_user_{self.sequence}",
            password="test1234",
            role="caregiver",
        )
        caregiver = Caregiver.objects.create(user=user, caregiver_type="formal")
        elderly = Elderly.objects.create(
            first_name=f"Adulto{self.sequence}",
            last_name="Mayor",
            age=80,
            caregiver=caregiver,
            relationship_to_caregiver="Hija",
            dependency_level="media",
            underlying_conditions="Hipertension",
        )
        if create_device and mac_address:
            Device.objects.create(
                name=f"ESP32 {self.sequence}",
                serial_number=f"SER-DISPATCH-{self.sequence}",
                mac_address=mac_address,
                model="ESP32",
                status="assigned",
                elderly=elderly,
            )
        activity = Activity.objects.create(
            title=f"Actividad {self.sequence}",
            description=f"Descripcion {self.sequence}",
            category=self.category,
        )
        return Assignment.objects.create(
            elderly=elderly,
            activity=activity,
            date=date,
            notification_time=notification_time,
            additional_instructions="",
            status=status,
        )


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

    def test_orchestrates_audio_whisper_interpretation_and_assignment_services(self):
        audio_service = Mock()
        whisper_service = Mock()
        response_service = Mock()
        assignment_response_service = Mock()

        audio_service.process.return_value = np.array([0.0, 0.1], dtype=np.float32)
        whisper_service.transcribe.return_value = "ya hice la actividad"
        response_service.interpret_assignment_response.return_value = {
            "transcription": "ya hice la actividad",
            "normalized_transcription": "ya hice la actividad",
            "was_interpreted": True,
            "result": "completed",
        }
        assignment = Mock()
        assignment.id = 77
        assignment.status = "completed"
        assignment_response_service.register_response.return_value = {
            "assignment": assignment,
            "assignment_updated": True,
        }

        service = VoiceAssistantService(
            audio_service=audio_service,
            whisper_service=whisper_service,
            response_service=response_service,
            assignment_response_service=assignment_response_service,
        )

        uploaded_file = SimpleUploadedFile("audio.wav", b"1234", content_type="audio/wav")
        result = service.process_assignment_response_file(
            audio_file=uploaded_file,
            mac_address="AA:BB:CC:DD:EE:01",
            assignment_id=77,
            sample_rate=DEFAULT_AUDIO_SAMPLE_RATE,
        )

        self.assertEqual(result["result"], "completed")
        self.assertEqual(result["assignment_status"], "completed")
        audio_service.process.assert_called_once_with(
            uploaded_file,
            sample_rate=DEFAULT_AUDIO_SAMPLE_RATE,
        )
        whisper_service.transcribe.assert_called_once()
        response_service.interpret_assignment_response.assert_called_once_with(
            "ya hice la actividad"
        )
        assignment_response_service.register_response.assert_called_once_with(
            mac_address="AA:BB:CC:DD:EE:01",
            assignment_id=77,
            transcription="ya hice la actividad",
            result="completed",
        )

    def test_orchestrates_pcm16_audio_whisper_and_assignment_services(self):
        audio_service = Mock()
        whisper_service = Mock()
        response_service = Mock()
        assignment_response_service = Mock()

        audio_service.process_pcm16_stream.return_value = np.array([0.0, 0.1], dtype=np.float32)
        whisper_service.transcribe.return_value = "no pude hacerla"
        response_service.interpret_assignment_response.return_value = {
            "transcription": "no pude hacerla",
            "normalized_transcription": "no pude hacerla",
            "was_interpreted": True,
            "result": "missed",
        }
        assignment = Mock()
        assignment.id = 55
        assignment.status = "missed"
        assignment_response_service.register_response.return_value = {
            "assignment": assignment,
            "assignment_updated": True,
        }

        service = VoiceAssistantService(
            audio_service=audio_service,
            whisper_service=whisper_service,
            response_service=response_service,
            assignment_response_service=assignment_response_service,
        )

        result = service.process_assignment_response_stream(
            audio_bytes=b"1234",
            mac_address="AA:BB:CC:DD:EE:02",
            assignment_id=55,
            sample_rate=DEFAULT_AUDIO_SAMPLE_RATE,
        )

        self.assertEqual(result["result"], "missed")
        audio_service.process_pcm16_stream.assert_called_once_with(
            b"1234",
            sample_rate=DEFAULT_AUDIO_SAMPLE_RATE,
        )
        whisper_service.transcribe.assert_called_once()
        response_service.interpret_assignment_response.assert_called_once_with(
            "no pude hacerla"
        )
        assignment_response_service.register_response.assert_called_once_with(
            mac_address="AA:BB:CC:DD:EE:02",
            assignment_id=55,
            transcription="no pude hacerla",
            result="missed",
        )

    def test_realistic_pcm16_fixture_reaches_whisper_without_state_change_when_ambiguous(self):
        raw_pcm = self.fixture_path.read_bytes()
        whisper_service = Mock()
        response_service = Mock()
        assignment_response_service = Mock()

        whisper_service.transcribe.return_value = ""
        response_service.interpret_assignment_response.return_value = {
            "transcription": "",
            "normalized_transcription": "",
            "was_interpreted": False,
            "result": VOICE_RESPONSE_UNKNOWN_RESULT,
        }
        assignment = Mock()
        assignment.id = 90
        assignment.status = "pending"
        assignment_response_service.register_response.return_value = {
            "assignment": assignment,
            "assignment_updated": False,
        }

        service = VoiceAssistantService(
            whisper_service=whisper_service,
            response_service=response_service,
            assignment_response_service=assignment_response_service,
        )

        result = service.process_assignment_response_stream(
            audio_bytes=raw_pcm,
            mac_address="AA:BB:CC:DD:EE:03",
            assignment_id=90,
            sample_rate=DEFAULT_AUDIO_SAMPLE_RATE,
        )

        self.assertEqual(result["result"], VOICE_RESPONSE_UNKNOWN_RESULT)
        self.assertFalse(result["assignment_updated"])
        whisper_service.transcribe.assert_called_once()
        response_service.interpret_assignment_response.assert_called_once_with("")

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
