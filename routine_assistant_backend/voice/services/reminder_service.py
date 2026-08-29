"""Services related to assignment reminders and status updates."""

from datetime import timedelta

from django.utils import timezone

from routines.models import Assignment
from users.models import Device


class ReminderService:
    """Service responsible for querying and updating routine reminders.

    This service centralizes all access related to Assignment records used by
    the voice assistant flow, such as retrieving due reminders and locating the
    next pending reminder for a specific elderly profile.
    """

    def _get_elderly_id_from_mac(self, mac_address):
        if not mac_address:
            return None

        device = (
            Device.objects.select_related("elderly")
            .filter(mac_address__iexact=mac_address.strip())
            .first()
        )

        if not device or not device.elderly_id:
            return None

        return device.elderly_id

    def _base_pending_assignments_queryset(self, elderly_id=None, target_date=None):
        """Return the shared base queryset for pending assignments."""

        queryset = Assignment.objects.filter(status="pending").select_related(
            "activity",
            "elderly",
        )

        if elderly_id is not None:
            queryset = queryset.filter(elderly_id=elderly_id)

        if target_date is not None:
            queryset = queryset.filter(date=target_date)

        return queryset

    def get_due_assignments(self, mac_address):
        """Return pending assignments due for processing at the current time.

        This method resolves the elderly profile assigned to the provided
        device MAC address and retrieves today's pending Assignment records
        whose notification time has already been reached, ordered from the
        earliest scheduled time to the latest.
        """
        now = timezone.localtime()
        current_date = now.date()
        current_time = now.time()
        elderly_id = self._get_elderly_id_from_mac(mac_address)

        if elderly_id is None:
            return Assignment.objects.none()

        return (
            self._base_pending_assignments_queryset(
                elderly_id=elderly_id,
                target_date=current_date,
            )
            .filter(notification_time__lte=current_time)
            .order_by("notification_time")
        )

    def get_next_pending_assignment(self, mac_address):
        """Return the next pending assignment for an elderly profile today.

        This method resolves the elderly profile assigned to the provided
        device MAC address and retrieves the first Assignment scheduled later
        today, as long as it remains pending.
        """
        now = timezone.localtime()
        current_date = now.date()
        current_time = now.time()
        elderly_id = self._get_elderly_id_from_mac(mac_address)

        if elderly_id is None:
            return None

        return (
            self._base_pending_assignments_queryset(
                elderly_id=elderly_id,
                target_date=current_date,
            )
            .filter(notification_time__gt=current_time)
            .order_by("notification_time")
            .first()
        )

    def get_assignments_due_for_dispatch(self, reference_datetime=None):
        """Return pending assignments scheduled within the current minute."""

        current_datetime = timezone.localtime(reference_datetime or timezone.now())
        current_date = current_datetime.date()
        minute_start = current_datetime.replace(second=0, microsecond=0)
        minute_end = minute_start + timedelta(minutes=1)

        return (
            self._base_pending_assignments_queryset(target_date=current_date)
            .filter(
                notification_time__gte=minute_start.time(),
                notification_time__lt=minute_end.time(),
            )
            .order_by("notification_time")
        )

    def get_device_for_elderly(self, elderly):
        """Return the device assigned to an elderly profile, if any."""

        if elderly is None:
            return None

        return Device.objects.filter(elderly=elderly).first()

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
