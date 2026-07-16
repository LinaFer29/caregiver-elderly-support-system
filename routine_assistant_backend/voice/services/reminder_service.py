"""Services related to assignment reminders and status updates."""

from django.utils import timezone

from routines.models import Assignment


class ReminderService:
    """Service responsible for querying and updating routine reminders.

    This service centralizes all access related to Assignment records used by
    the voice assistant flow, such as retrieving due reminders and locating the
    next pending reminder for a specific elderly profile.
    """

    def get_due_assignments(self, elderly_id):
        """Return pending assignments due for processing at the current time.

        This method retrieves today's Assignment records whose notification time
        has already been reached for the provided elderly profile and that are
        still pending, ordered from the earliest scheduled time to the latest.
        """
        now = timezone.localtime()
        current_date = now.date()
        current_time = now.time()

        return (
            Assignment.objects.filter(
                elderly_id=elderly_id,
                status="pending",
                date=current_date,
                notification_time__lte=current_time,
            )
            .select_related("activity", "elderly")
            .order_by("notification_time")
        )

    def get_next_pending_assignment(self, elderly_id):
        """Return the next pending assignment for an elderly profile today.

        This method retrieves the first Assignment scheduled later today for
        the provided elderly profile, as long as it remains pending.
        """
        now = timezone.localtime()
        current_date = now.date()
        current_time = now.time()

        return (
            Assignment.objects.filter(
                elderly_id=elderly_id,
                status="pending",
                date=current_date,
                notification_time__gt=current_time,
            )
            .order_by("notification_time")
            .first()
        )

    def mark_completed(self):
        """Mark an assignment as completed.

        In a future iteration, this method will update the corresponding
        Assignment record to reflect a successful completion and store any
        complementary execution details required by the assistant.
        """
        raise NotImplementedError

    def mark_missed(self):
        """Mark an assignment as missed.

        In a future iteration, this method will update the corresponding
        Assignment record when the reminder was not completed within the
        expected time window.
        """
        raise NotImplementedError
