"""Query services for caregiver-facing routine and assignment views."""

from django.db.models import Count
from django.utils import timezone

from routines.models import Assignment, Program


class RoutineQueryService:
    """Centralize operational routine queries shown in the caregiver frontend."""

    def get_current_date(self):
        """Return the local application date used for operational filtering."""

        return timezone.localdate()

    def get_visible_programs_queryset(self, caregiver, elderly_id=None):
        """Return program records visible in the caregiver frontend."""

        queryset = Program.objects.filter(
            caregiver=caregiver,
            elderly__caregiver=caregiver,
            date__gte=self.get_current_date(),
        ).select_related("activity", "activity__category", "elderly")

        if elderly_id is not None:
            queryset = queryset.filter(elderly_id=elderly_id)

        return queryset.order_by("date", "time", "id")

    def get_visible_assignments_queryset(self, elderly):
        """Return assignment records visible in the caregiver frontend."""

        return (
            Assignment.objects.filter(
                elderly=elderly,
                date__gte=self.get_current_date(),
            )
            .select_related("activity", "activity__category", "elderly")
            .order_by("date", "notification_time", "id")
        )

    def list_visible_routines(self, caregiver, elderly):
        """Return routine payloads grouped by date for current/future dates."""

        assignments = list(self.get_visible_assignments_queryset(elderly))
        if not assignments:
            return []

        routine_dates = []
        seen_dates = set()
        for assignment in assignments:
            if assignment.date in seen_dates:
                continue

            seen_dates.add(assignment.date)
            routine_dates.append(assignment.date)

        program_map = self._build_program_map(caregiver, elderly, routine_dates)
        grouped_assignments = self._group_assignments_by_date(assignments)

        return [
            self.build_routine_payload(
                caregiver=caregiver,
                elderly=elderly,
                date_value=date_value,
                assignments=grouped_assignments.get(date_value, []),
                program_map=program_map,
            )
            for date_value in routine_dates
        ]

    def get_visible_routine(self, caregiver, elderly, date_value):
        """Return one visible routine payload or None if the date is not visible."""

        if date_value < self.get_current_date():
            return None

        assignments = list(
            self.get_visible_assignments_queryset(elderly).filter(date=date_value)
        )
        if not assignments:
            return None

        program_map = self._build_program_map(caregiver, elderly, [date_value])
        return self.build_routine_payload(
            caregiver=caregiver,
            elderly=elderly,
            date_value=date_value,
            assignments=assignments,
            program_map=program_map,
        )

    def get_daily_assignment_summary(self, elderly):
        """Return today's assignment counts grouped by status."""

        today = self.get_current_date()
        grouped_counts = {
            item["status"]: item["count"]
            for item in (
                Assignment.objects.filter(elderly=elderly, date=today)
                .values("status")
                .annotate(count=Count("id"))
            )
        }

        completed = grouped_counts.get("completed", 0)
        missed = grouped_counts.get("missed", 0)
        pending = grouped_counts.get("pending", 0)
        total = completed + missed + pending

        return {
            "date": today.isoformat(),
            "total": total,
            "completed": completed,
            "missed": missed,
            "pending": pending,
        }

    def build_routine_payload(
        self,
        caregiver,
        elderly,
        date_value,
        assignments=None,
        program_map=None,
    ):
        """Build the caregiver-facing routine payload for one date."""

        assignments = assignments or list(
            self.get_visible_assignments_queryset(elderly).filter(date=date_value)
        )
        if program_map is None:
            program_map = self._build_program_map(caregiver, elderly, [date_value])

        items = []
        for assignment in assignments:
            program = program_map.get(
                (
                    assignment.activity_id,
                    assignment.date,
                    assignment.notification_time,
                )
            )

            items.append(
                {
                    "activity_id": assignment.activity.id,
                    "title": assignment.activity.title,
                    "description": assignment.activity.description,
                    "category_name": assignment.activity.category.name,
                    "category_color": assignment.activity.category.color,
                    "time": assignment.notification_time.strftime("%H:%M:%S"),
                    "frequency": program.frequency if program else "daily",
                    "is_active": program.is_active if program else True,
                    "status": assignment.status,
                    "additional_instructions": assignment.additional_instructions,
                }
            )

        has_inactive = any(not item["is_active"] for item in items)
        all_completed = len(items) > 0 and all(
            item["status"] == "completed" for item in items
        )

        general_status = "active"
        if has_inactive:
            general_status = "mixed"
        if all_completed:
            general_status = "completed"

        return {
            "id": f"{elderly.id}|{date_value.isoformat()}",
            "date": date_value.isoformat(),
            "elderly": {
                "id": elderly.id,
                "first_name": elderly.first_name,
                "last_name": elderly.last_name,
            },
            "items": items,
            "activities_count": len(items),
            "general_status": general_status,
        }

    def _build_program_map(self, caregiver, elderly, date_values):
        """Index visible programs by activity/date/time for quick assignment joins."""

        if not date_values:
            return {}

        programs = self.get_visible_programs_queryset(
            caregiver=caregiver,
            elderly_id=elderly.id,
        ).filter(date__in=date_values)

        return {
            (program.activity_id, program.date, program.time): program
            for program in programs
        }

    def _group_assignments_by_date(self, assignments):
        """Group assignments by date while preserving query ordering."""

        grouped = {}
        for assignment in assignments:
            grouped.setdefault(assignment.date, []).append(assignment)
        return grouped
