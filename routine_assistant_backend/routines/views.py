from django.shortcuts import get_object_or_404, render
from datetime import datetime

from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from activities.models import Activity
from users.models import Caregiver, Elderly
from .models import Assignment, Program
from .serializers import (
    ActivityWithProgramSerializer,
    AssignmentSerializer,
    ProgramSerializer,
    RoutineCatalogActivitySerializer,
    RoutineCreateSerializer,
)
from .utils import generate_dates
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction


# Create your views here.
class ProgramViewSet(viewsets.ModelViewSet):
    queryset = Program.objects.all()
    serializer_class = ProgramSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Program.objects.filter(
            caregiver__user=self.request.user,
            elderly__caregiver__user=self.request.user,
        )
        elderly_id = self.request.query_params.get("elderly_id")
        if elderly_id:
            queryset = queryset.filter(elderly_id=elderly_id)
        return queryset

    def perform_create(self, serializer):
        caregiver = get_object_or_404(Caregiver, user=self.request.user)
        elderly = get_object_or_404(
            Elderly,
            id=self.request.data.get("elderly"),
            caregiver=caregiver,
        )
        serializer.save(caregiver=caregiver, elderly=elderly)

    def perform_update(self, serializer):
        caregiver = Caregiver.objects.get(user=self.request.user)
        elderly_id = self.request.data.get("elderly")
        elderly = (
            get_object_or_404(Elderly, id=elderly_id, caregiver=caregiver)
            if elderly_id
            else serializer.instance.elderly
        )
        serializer.save(caregiver=caregiver, elderly=elderly)


class AssigmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer


class ActivitiesWithProgramView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        caregiver = Caregiver.objects.get(user=request.user)
        elderly_id = request.query_params.get("elderly_id")

        programs = Program.objects.filter(caregiver=caregiver).select_related(
            "activity", "elderly"
        )
        if elderly_id:
            programs = programs.filter(elderly_id=elderly_id)

        activities = [program.activity for program in programs]

        serializer = ActivityWithProgramSerializer(
            activities,
            many=True,
            context={
                "caregiver": caregiver,
                "elderly_id": int(elderly_id) if elderly_id else None,
            },
        )

        return Response(serializer.data)

    def post(self, request):
        caregiver = Caregiver.objects.get(user=request.user)

        elderly_id = request.data.get("elderly_id")
        elderly = get_object_or_404(Elderly, id=elderly_id, caregiver=caregiver)

        with transaction.atomic():

            # 1. Crear Activity
            activity = Activity.objects.create(
                title=request.data.get("title"),
                description=request.data.get("description"),
                category_id=request.data.get("category"),
            )

            # 2. Crear Program
            program = Program.objects.create(
                caregiver=caregiver,
                elderly=elderly,
                activity=activity,
                date=request.data.get("date"),
                time=request.data.get("time"),
                frequency=request.data.get("frequency"),
                is_active=request.data.get("is_active", False),
            )

            # 3. Crear Assignment
            assignment = Assignment.objects.create(
                elderly=elderly,
                activity=activity,
                date=request.data.get("date"),
                notification_time=request.data.get("time"),
                additional_instructions=request.data.get("additional_instructions"),
                status="pending",
            )

        return Response(
            {
                "activity_id": activity.id,
                "program_id": program.id,
                "assignment_id": assignment.id,
            },
            status=status.HTTP_201_CREATED,
        )

    def put(self, request, activity_id):
        caregiver = Caregiver.objects.get(user=request.user)

        # Obtener Activity asegurando que pertenece al usuario
        activity = get_object_or_404(
            Activity, id=activity_id, program__caregiver=caregiver
        )

        # Obtener Program asociado
        elderly_id = request.data.get("elderly_id")
        if elderly_id:
            elderly = get_object_or_404(Elderly, id=elderly_id, caregiver=caregiver)
            program = get_object_or_404(
                Program,
                activity=activity,
                caregiver=caregiver,
                elderly=elderly,
            )
        else:
            program = get_object_or_404(Program, activity=activity, caregiver=caregiver)

        with transaction.atomic():

            # 1. Actualizar Activity
            activity.title = request.data.get("title", activity.title)
            activity.description = request.data.get("description", activity.description)
            activity.category_id = request.data.get("category", activity.category_id)
            activity.save()

            # 2. Actualizar Program
            program.date = request.data.get("date", program.date)
            program.time = request.data.get("time", program.time)
            program.frequency = request.data.get("frequency", program.frequency)
            program.is_active = request.data.get("is_active", program.is_active)
            program.save()

        return Response({"message": "Actividad actualizada correctamente"}, status=200)


class RoutineCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        activities = Activity.objects.select_related("category").all()
        serializer = RoutineCatalogActivitySerializer(activities, many=True)
        return Response(serializer.data)


class RoutineCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def _parse_routine_id(self, routine_id: str):
        try:
            elderly_id, date_str = routine_id.split("|", 1)
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            return int(elderly_id), parsed_date
        except (ValueError, TypeError):
            return None, None

    def _build_routine_payload(self, caregiver, elderly, date_value):
        assignments = (
            Assignment.objects.filter(elderly=elderly, date=date_value)
            .select_related("activity", "activity__category")
            .order_by("notification_time")
        )

        items = []
        for assignment in assignments:
            program = Program.objects.filter(
                caregiver=caregiver,
                elderly=elderly,
                activity=assignment.activity,
                date=assignment.date,
                time=assignment.notification_time,
            ).first()

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

    def get(self, request, routine_id=None):
        caregiver = Caregiver.objects.get(user=request.user)

        if routine_id is not None:
            elderly_id, routine_date = self._parse_routine_id(routine_id)
            if not elderly_id or not routine_date:
                return Response({"detail": "routine_id inválido."}, status=400)

            elderly = get_object_or_404(Elderly, id=elderly_id, caregiver=caregiver)
            assignments = Assignment.objects.filter(elderly=elderly, date=routine_date)
            if not assignments.exists():
                return Response({"detail": "Rutina no encontrada."}, status=404)

            return Response(
                self._build_routine_payload(caregiver, elderly, routine_date)
            )

        elderly_id = request.query_params.get("elderly_id")

        if not elderly_id:
            return Response({"detail": "elderly_id es requerido."}, status=400)

        elderly = get_object_or_404(Elderly, id=elderly_id, caregiver=caregiver)

        assignments = (
            Assignment.objects.filter(elderly=elderly)
            .select_related("activity", "activity__category")
            .order_by("date", "notification_time")
        )

        dates = []
        seen_dates = set()
        for assignment in assignments:
            if assignment.date not in seen_dates:
                seen_dates.add(assignment.date)
                dates.append(assignment.date)

        routines = [
            self._build_routine_payload(caregiver, elderly, date_value)
            for date_value in dates
        ]
        return Response(routines)

    def post(self, request):
        payload = request.data.copy()

        # Compatibilidad con payload antiguo: activity_ids + time/frequency/is_active global
        if "activities" not in payload and "activity_ids" in payload:
            activity_ids = payload.get("activity_ids", [])
            global_time = payload.get("time")
            global_frequency = payload.get("frequency", "once")
            global_is_active = payload.get("is_active", True)
            legacy_date = payload.get("date")
            if "start_date" not in payload and legacy_date:
                payload["start_date"] = legacy_date
            if "end_date" not in payload and legacy_date:
                payload["end_date"] = legacy_date
            payload["activities"] = [
                {
                    "activity_id": int(activity_id),
                    "time": global_time,
                    "frequency": global_frequency,
                    "is_active": global_is_active,
                    "additional_instructions": payload.get(
                        "additional_instructions", ""
                    ),
                }
                for activity_id in activity_ids
            ]

        serializer = RoutineCreateSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        caregiver = Caregiver.objects.get(user=request.user)
        elderly = get_object_or_404(
            Elderly, id=serializer.validated_data["elderly_id"], caregiver=caregiver
        )

        activity_ids = [
            item["activity_id"] for item in serializer.validated_data["activities"]
        ]
        activities = list(
            Activity.objects.filter(id__in=activity_ids).select_related("category")
        )

        if len(activities) != len(set(activity_ids)):
            return Response(
                {"detail": "Una o más actividades no existen."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_program_ids = []
        created_assignment_ids = []

        with transaction.atomic():
            activity_map = {activity.id: activity for activity in activities}

            for item in serializer.validated_data["activities"]:
                activity = activity_map[item["activity_id"]]

                occurrence_dates = generate_dates(
                    serializer.validated_data["start_date"],
                    serializer.validated_data["end_date"],
                    item["frequency"],
                )

                for occurrence_date in occurrence_dates:
                    program = Program.objects.create(
                        caregiver=caregiver,
                        elderly=elderly,
                        activity=activity,
                        date=occurrence_date,
                        time=item["time"],
                        frequency=item["frequency"],
                        is_active=item["is_active"],
                    )
                    created_program_ids.append(program.id)

                    assignment = Assignment.objects.create(
                        elderly=elderly,
                        activity=activity,
                        date=occurrence_date,
                        notification_time=item["time"],
                        additional_instructions=item.get("additional_instructions"),
                        status="pending",
                    )
                    created_assignment_ids.append(assignment.id)

        return Response(
            {
                "elderly_id": elderly.id,
                "activities_count": len(activities),
                "program_ids": created_program_ids,
                "assignment_ids": created_assignment_ids,
                "scheduled_occurrences_count": len(created_assignment_ids),
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, routine_id):
        caregiver = Caregiver.objects.get(user=request.user)
        elderly_id, routine_date = self._parse_routine_id(routine_id)

        if not elderly_id or not routine_date:
            return Response({"detail": "routine_id inválido."}, status=400)

        elderly = get_object_or_404(Elderly, id=elderly_id, caregiver=caregiver)

        assignments = Assignment.objects.filter(elderly=elderly, date=routine_date)

        if not assignments.exists():
            return Response({"detail": "Rutina no encontrada."}, status=404)

        with transaction.atomic():
            Program.objects.filter(
                caregiver=caregiver,
                elderly=elderly,
                date=routine_date,
            ).delete()
            assignments.delete()

        return Response(status=204)

    def put(self, request, routine_id):
        caregiver = Caregiver.objects.get(user=request.user)
        elderly_id, routine_date = self._parse_routine_id(routine_id)

        if not elderly_id or not routine_date:
            return Response({"detail": "routine_id inválido."}, status=400)

        elderly = get_object_or_404(Elderly, id=elderly_id, caregiver=caregiver)

        payload = request.data.copy()
        payload["elderly_id"] = elderly.id
        if "start_date" not in payload and "date" in payload:
            payload["start_date"] = payload["date"]
        if "end_date" not in payload and "date" in payload:
            payload["end_date"] = payload["date"]
        serializer = RoutineCreateSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        existing_assignments = list(
            Assignment.objects.filter(elderly=elderly, date=routine_date)
        )

        if not existing_assignments:
            return Response({"detail": "Rutina no encontrada."}, status=404)

        activity_ids = [
            item["activity_id"] for item in serializer.validated_data["activities"]
        ]
        activities = list(Activity.objects.filter(id__in=activity_ids))

        if len(activities) != len(set(activity_ids)):
            return Response(
                {"detail": "Una o más actividades no existen."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            Program.objects.filter(
                caregiver=caregiver,
                elderly=elderly,
                date=routine_date,
            ).delete()
            Assignment.objects.filter(elderly=elderly, date=routine_date).delete()

            activity_map = {activity.id: activity for activity in activities}
            for item in serializer.validated_data["activities"]:
                activity = activity_map[item["activity_id"]]
                occurrence_dates = generate_dates(
                    serializer.validated_data["start_date"],
                    serializer.validated_data["end_date"],
                    item["frequency"],
                )

                for occurrence_date in occurrence_dates:
                    Program.objects.create(
                        caregiver=caregiver,
                        elderly=elderly,
                        activity=activity,
                        date=occurrence_date,
                        time=item["time"],
                        frequency=item["frequency"],
                        is_active=item["is_active"],
                    )

                    Assignment.objects.create(
                        elderly=elderly,
                        activity=activity,
                        date=occurrence_date,
                        notification_time=item["time"],
                        additional_instructions=item.get("additional_instructions"),
                        status="pending",
                    )

        updated_date = serializer.validated_data["start_date"]
        return Response(
            self._build_routine_payload(caregiver, elderly, updated_date), status=200
        )
