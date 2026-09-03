from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from activities.models import Activity, Category
from routines.models import Assignment, Program
from routines.services.query_service import RoutineQueryService
from users.models import Caregiver, Elderly, User


class BaseRoutineFixtureMixin:
    def setUp(self):
        super().setUp()
        self.current_date = timezone.localdate()
        self.user = User.objects.create_user(
            username="caregiver1",
            password="secret123",
            role="caregiver",
        )
        self.caregiver = Caregiver.objects.create(
            user=self.user,
            caregiver_type="familiar",
        )
        self.elderly = Elderly.objects.create(
            first_name="Ana",
            last_name="Lopez",
            age=74,
            caregiver=self.caregiver,
            relationship_to_caregiver="Hija",
            dependency_level="moderado",
            underlying_conditions="Hipertensión",
        )
        self.category = Category.objects.create(
            name="Salud",
            color="#00AA88",
            icon="heart",
        )
        self.activity_past = Activity.objects.create(
            title="Actividad pasada",
            description="Descripción pasada",
            category=self.category,
        )
        self.activity_today_completed = Activity.objects.create(
            title="Medicamento mañana",
            description="Tomar medicación",
            category=self.category,
        )
        self.activity_today_missed = Activity.objects.create(
            title="Tomar agua",
            description="Hidratarse",
            category=self.category,
        )
        self.activity_today_pending = Activity.objects.create(
            title="Caminar",
            description="Salir a caminar",
            category=self.category,
        )
        self.activity_future = Activity.objects.create(
            title="Actividad futura",
            description="Descripción futura",
            category=self.category,
        )

        self._create_program_and_assignment(
            activity=self.activity_past,
            date_value=self.current_date - timedelta(days=1),
            time_value="07:00",
            status="completed",
            is_active=True,
        )
        self.today_completed = self._create_program_and_assignment(
            activity=self.activity_today_completed,
            date_value=self.current_date,
            time_value="08:00",
            status="completed",
            is_active=True,
        )
        self.today_missed = self._create_program_and_assignment(
            activity=self.activity_today_missed,
            date_value=self.current_date,
            time_value="09:00",
            status="missed",
            is_active=False,
        )
        self.today_pending = self._create_program_and_assignment(
            activity=self.activity_today_pending,
            date_value=self.current_date,
            time_value="10:00",
            status="pending",
            is_active=True,
        )
        self.future_pending = self._create_program_and_assignment(
            activity=self.activity_future,
            date_value=self.current_date + timedelta(days=1),
            time_value="11:00",
            status="pending",
            is_active=True,
        )

    def _create_program_and_assignment(
        self,
        *,
        activity,
        date_value,
        time_value,
        status,
        is_active,
    ):
        program = Program.objects.create(
            caregiver=self.caregiver,
            elderly=self.elderly,
            activity=activity,
            date=date_value,
            time=time_value,
            frequency="once",
            is_active=is_active,
        )
        assignment = Assignment.objects.create(
            elderly=self.elderly,
            activity=activity,
            date=date_value,
            notification_time=time_value,
            status=status,
            additional_instructions="",
        )
        return {"program": program, "assignment": assignment}


class RoutineQueryServiceTests(BaseRoutineFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.service = RoutineQueryService()

    def test_list_visible_routines_excludes_past_dates(self):
        routines = self.service.list_visible_routines(
            caregiver=self.caregiver,
            elderly=self.elderly,
        )

        self.assertEqual(
            [routine["date"] for routine in routines],
            [
                self.current_date.isoformat(),
                (self.current_date + timedelta(days=1)).isoformat(),
            ],
        )

    def test_daily_summary_counts_today_assignments_by_status(self):
        summary = self.service.get_daily_assignment_summary(self.elderly)

        self.assertEqual(summary["date"], self.current_date.isoformat())
        self.assertEqual(summary["completed"], 1)
        self.assertEqual(summary["missed"], 1)
        self.assertEqual(summary["pending"], 1)
        self.assertEqual(summary["total"], 3)

    def test_historical_records_remain_in_database(self):
        past_date = self.current_date - timedelta(days=1)

        self.assertTrue(
            Assignment.objects.filter(
                elderly=self.elderly,
                date=past_date,
            ).exists()
        )
        self.assertTrue(
            Program.objects.filter(
                elderly=self.elderly,
                date=past_date,
            ).exists()
        )


class RoutineFrontendApiTests(BaseRoutineFixtureMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_routines_endpoint_returns_only_current_and_future_dates(self):
        response = self.client.get(
            "/api/v1/routines/",
            {"elderly_id": self.elderly.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["date"] for item in response.json()],
            [
                self.current_date.isoformat(),
                (self.current_date + timedelta(days=1)).isoformat(),
            ],
        )

    def test_routine_detail_returns_404_for_past_date(self):
        past_routine_id = f"{self.elderly.id}|{(self.current_date - timedelta(days=1)).isoformat()}"

        response = self.client.get(f"/api/v1/routines/{past_routine_id}/")

        self.assertEqual(response.status_code, 404)

    def test_daily_summary_endpoint_returns_assignment_counts(self):
        response = self.client.get(
            "/api/v1/routines/daily-summary/",
            {"elderly_id": self.elderly.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "date": self.current_date.isoformat(),
                "total": 3,
                "completed": 1,
                "missed": 1,
                "pending": 1,
            },
        )

    def test_programs_endpoint_hides_past_dates(self):
        response = self.client.get(
            "/api/v1/programs/",
            {"elderly_id": self.elderly.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 4)
        self.assertTrue(
            all(item["date"] >= self.current_date.isoformat() for item in response.json())
        )

    def test_activities_with_program_uses_visible_program_date(self):
        shared_activity = Activity.objects.create(
            title="Glucosa",
            description="Medir glucosa",
            category=self.category,
        )
        Program.objects.create(
            caregiver=self.caregiver,
            elderly=self.elderly,
            activity=shared_activity,
            date=self.current_date - timedelta(days=3),
            time="06:00",
            frequency="once",
            is_active=True,
        )
        Program.objects.create(
            caregiver=self.caregiver,
            elderly=self.elderly,
            activity=shared_activity,
            date=self.current_date + timedelta(days=2),
            time="07:30",
            frequency="once",
            is_active=True,
        )

        response = self.client.get(
            "/api/v1/activities-with-program/",
            {"elderly_id": self.elderly.id},
        )

        self.assertEqual(response.status_code, 200)
        matching_items = [
            item for item in response.json() if item["id"] == shared_activity.id
        ]
        self.assertEqual(len(matching_items), 1)
        self.assertEqual(
            matching_items[0]["program"]["date"],
            (self.current_date + timedelta(days=2)).isoformat(),
        )

    def test_visibility_filter_does_not_change_assignment_status(self):
        response = self.client.get(
            "/api/v1/routines/daily-summary/",
            {"elderly_id": self.elderly.id},
        )

        self.assertEqual(response.status_code, 200)
        self.today_completed["assignment"].refresh_from_db()
        self.today_missed["assignment"].refresh_from_db()
        self.today_pending["assignment"].refresh_from_db()

        self.assertEqual(self.today_completed["assignment"].status, "completed")
        self.assertEqual(self.today_missed["assignment"].status, "missed")
        self.assertEqual(self.today_pending["assignment"].status, "pending")
