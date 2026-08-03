"""Services related to the voice assistant orchestration workflow."""

from .audio_service import AudioProcessingService
from .reminder_service import ReminderService
from .response_service import ResponseService
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
    ):
        """Initialize the service with its reminder dependency."""

        self.reminder_service = reminder_service or ReminderService()
        self.audio_service = audio_service or AudioProcessingService()
        self.whisper_service = whisper_service or WhisperService()
        self.response_service = response_service or ResponseService()

    def get_due_reminders(self, mac_address):
        """Build the reminder payload consumed by the voice assistant.

        This method retrieves due Assignment records through ReminderService
        and transforms them into a compact, human-readable response payload for
        the external assistant device, without accessing persistence directly.
        """

        reminders = []
        assignments = self.reminder_service.get_due_assignments(mac_address)

        for assignment in assignments:
            instructions = (assignment.additional_instructions or "").strip()
            if instructions:
                message = (
                    f"Es hora de {assignment.activity.title}. "
                    f"{instructions}"
                )
            else:
                message = (
                    f"Es hora de {assignment.activity.title}. "
                    f"{assignment.activity.description}"
                )

            reminders.append(
                {
                    "assignment_id": assignment.id,
                    "elderly_id": assignment.elderly_id,
                    "activity": assignment.activity.title,
                    "message": message,
                    "scheduled_time": assignment.notification_time,
                }
            )

        return reminders

    def process_speech_command(self, audio_file, sample_rate=None):
        """Process an uploaded audio file and resolve the assistant response."""

        waveform = self.audio_service.process(audio_file, sample_rate=sample_rate)
        transcription = self.whisper_service.transcribe(waveform)
        return self.response_service.build_response(transcription)

    def process_pcm16_command(self, audio_bytes, sample_rate=None):
        """Process a raw PCM16 stream and resolve the assistant response."""

        waveform = self.audio_service.process_pcm16_stream(
            audio_bytes,
            sample_rate=sample_rate,
        )
        transcription = self.whisper_service.transcribe(waveform)
        return self.response_service.build_response(transcription)
