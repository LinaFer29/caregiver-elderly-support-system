"""Services related to the voice assistant orchestration workflow."""

import re

from .assignment_response_service import AssignmentResponseService
from .audio_service import AudioProcessingService
from .reminder_service import ReminderService
from .response_service import ResponseService
from .tts_service import TTSService
from .whisper_service import WhisperService


class VoiceAssistantService:
    """Service responsible for future voice-assistant orchestration.

    This service is intended to coordinate higher-level voice assistant flows
    by delegating persistence and reminder operations to specialized services,
    such as ReminderService, without directly querying application models.
    """

    def __init__(
        self,
        reminder_service=None,
        audio_service=None,
        whisper_service=None,
        response_service=None,
        tts_service=None,
        assignment_response_service=None,
    ):
        """Initialize the service with its reminder dependency."""

        self.reminder_service = reminder_service or ReminderService()
        self.audio_service = audio_service or AudioProcessingService()
        self.whisper_service = whisper_service or WhisperService()
        self.response_service = response_service or ResponseService()
        self.tts_service = tts_service or TTSService()
        self.assignment_response_service = (
            assignment_response_service
            or AssignmentResponseService(reminder_service=self.reminder_service)
        )

    def get_due_reminders(self, mac_address):
        """Build the reminder payload consumed by the voice assistant.

        This method retrieves due Assignment records through ReminderService
        and transforms them into a compact, human-readable response payload for
        the external assistant device, without accessing persistence directly.
        """

        reminders = []
        assignments = self.reminder_service.get_due_assignments(mac_address)

        for assignment in assignments:
            reminders.append(self.build_due_reminder_payload(assignment))

        return reminders

    def build_due_reminder_payload(self, assignment):
        """Build the canonical reminder payload for one assignment.

        This is the shared source of truth used both by the HTTP reminders
        endpoint and by the MQTT publication flow, so audio generation and the
        resulting `audio_file` keep a single contract across transports.
        """

        message = self._build_reminder_message(assignment)
        tts_text = self._build_tts_message(
            activity=assignment.activity.title,
            message=message,
        )
        audio_reference = self.tts_service.generate_audio(
            text=tts_text,
            identifier=str(assignment.id),
        )

        return {
            "assignment_id": assignment.id,
            "elderly_id": assignment.elderly_id,
            "activity": assignment.activity.title,
            "message": message,
            "scheduled_time": assignment.notification_time,
            "audio_file": audio_reference["audio_file"],
        }

    def process_assignment_response_file(
        self,
        audio_file,
        mac_address,
        assignment_id,
        sample_rate=None,
    ):
        """Process multipart audio and update the corresponding assignment."""

        waveform = self.audio_service.process(audio_file, sample_rate=sample_rate)
        return self._resolve_assignment_response(
            waveform=waveform,
            mac_address=mac_address,
            assignment_id=assignment_id,
        )

    def process_assignment_response_stream(
        self,
        audio_bytes,
        mac_address,
        assignment_id,
        sample_rate=None,
    ):
        """Process raw PCM16 audio and update the corresponding assignment."""

        waveform = self.audio_service.process_pcm16_stream(
            audio_bytes,
            sample_rate=sample_rate,
        )
        return self._resolve_assignment_response(
            waveform=waveform,
            mac_address=mac_address,
            assignment_id=assignment_id,
        )

    def _resolve_assignment_response(self, waveform, mac_address, assignment_id):
        """Run STT, interpret the response and update the assignment state."""

        transcription = self.whisper_service.transcribe(waveform)
        interpretation = self.response_service.interpret_assignment_response(
            transcription
        )
        assignment_resolution = self.assignment_response_service.register_response(
            mac_address=mac_address,
            assignment_id=assignment_id,
            transcription=interpretation["transcription"],
            result=interpretation["result"],
        )
        assignment = assignment_resolution["assignment"]

        return {
            "audio_received": True,
            "stt_success": True,
            "transcription": interpretation["transcription"],
            "normalized_transcription": interpretation["normalized_transcription"],
            "was_interpreted": interpretation["was_interpreted"],
            "result": interpretation["result"],
            "assignment_id": assignment.id,
            "assignment_status": assignment.status,
            "assignment_updated": assignment_resolution["assignment_updated"],
        }

    def _build_reminder_message(self, assignment):
        """Build the reminder message from existing assignment data."""

        instructions = (assignment.additional_instructions or "").strip()
        if instructions:
            return f"Es hora de {assignment.activity.title}. {instructions}"

        return (
            f"Es hora de {assignment.activity.title}. "
            f"{assignment.activity.description}"
        )

    def _build_tts_message(self, activity, message):
        """Create a brief spoken message from the existing reminder payload."""

        cleaned_activity = " ".join((activity or "").split())
        cleaned_message = " ".join((message or "").split())

        if not cleaned_message:
            cleaned_message = f"Es hora de {cleaned_activity}."

        spoken_message = (
            "Hola, es momento de realizar una actividad. "
            f"{cleaned_message}"
        )
        return re.sub(r"\s+", " ", spoken_message).strip()
