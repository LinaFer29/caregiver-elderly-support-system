"""Services related to the voice assistant orchestration workflow."""

from .reminder_service import ReminderService


class VoiceAssistantService:
    """Service responsible for future voice-assistant orchestration.

    This service is intended to coordinate higher-level voice assistant flows
    by delegating persistence and reminder operations to specialized services,
    such as ReminderService, without directly querying application models.
    """

    def __init__(self, reminder_service=None):
        """Initialize the service with its reminder dependency."""

        self.reminder_service = reminder_service or ReminderService()

    def get_due_reminders(self, elderly_id):
        """Build the reminder payload consumed by the voice assistant.

        This method retrieves due Assignment records through ReminderService
        and transforms them into a compact, human-readable response payload for
        the external assistant device, without accessing persistence directly.
        """

        reminders = []
        assignments = self.reminder_service.get_due_assignments(elderly_id)

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
