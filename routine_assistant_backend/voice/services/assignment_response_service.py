"""Domain services for applying spoken responses to assignments."""

from django.utils import timezone

from .reminder_service import ReminderService


class AssignmentResponseService:
    """Resolve and update assignments based on interpreted spoken responses."""

    def __init__(self, reminder_service=None):
        self.reminder_service = reminder_service or ReminderService()

    def register_response(self, mac_address, assignment_id, transcription, result):
        """Store the spoken response and update assignment status when possible."""

        assignment = self.reminder_service.get_assignment_for_device_response(
            mac_address=mac_address,
            assignment_id=assignment_id,
        )

        update_fields = ["user_response", "response_time"]
        assignment.user_response = (transcription or "").strip()
        assignment.response_time = timezone.localtime().time()
        assignment_updated = False

        if assignment.status == "pending" and result in {"completed", "missed"}:
            assignment.status = result
            update_fields.append("status")
            assignment_updated = True

        assignment.save(update_fields=update_fields)

        return {
            "assignment": assignment,
            "assignment_updated": assignment_updated,
        }
