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
    DailyAssignmentSummarySerializer,
    ProgramSerializer,
    RoutineCatalogActivitySerializer,
    RoutineCreateSerializer,
)
from .services.query_service import RoutineQueryService
from .utils import generate_dates
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction


# Create your views here.
class ProgramViewSet(viewsets.ModelViewSet):
    queryset = Program.objects.all()
    serializer_class = ProgramSerializer
    permission_classes = [IsAuthenticated]
    query_service = RoutineQueryService()

    def get_queryset(self):
        caregiver = get_object_or_404(Caregiver, user=self.request.user)
        elderly_id = self.request.query_params.get("elderly_id")
        return self.query_service.get_visible_programs_queryset(
            caregiver=caregiver,
            elderly_id=elderly_id,
        )

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
    query_service = RoutineQueryService()

    def get(self, request):
        caregiver = Caregiver.objects.get(user=request.user)
        elderly_id = request.query_params.get("elderly_id")

        programs = self.query_service.get_visible_programs_queryset(
            caregiver=caregiver,
            elderly_id=int(elderly_id) if elderly_id else None,
        )

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
    query_service = RoutineQueryService()

    def _parse_routine_id(self, routine_id: str):
        try:
            elderly_id, date_str = routine_id.split("|", 1)
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            return int(elderly_id), parsed_date
        except (ValueError, TypeError):
            return None, None

    def get(self, request, routine_id=None):
        caregiver = Caregiver.objects.get(user=request.user)

        if routine_id is not None:
            elderly_id, routine_date = self._parse_routine_id(routine_id)
            if not elderly_id or not routine_date:
                return Response({"detail": "routine_id inválido."}, status=400)

            elderly = get_object_or_404(Elderly, id=elderly_id, caregiver=caregiver)
            routine_payload = self.query_service.get_visible_routine(
                caregiver=caregiver,
                elderly=elderly,
                date_value=routine_date,
            )
            if routine_payload is None:
                return Response({"detail": "Rutina no encontrada."}, status=404)

            return Response(routine_payload)

        elderly_id = request.query_params.get("elderly_id")

        if not elderly_id:
            return Response({"detail": "elderly_id es requerido."}, status=400)

        elderly = get_object_or_404(Elderly, id=elderly_id, caregiver=caregiver)

        routines = self.query_service.list_visible_routines(
            caregiver=caregiver,
            elderly=elderly,
        )
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
            self.query_service.build_routine_payload(
                caregiver=caregiver,
                elderly=elderly,
                date_value=updated_date,
            ),
            status=200,
        )


class DailyAssignmentSummaryView(APIView):
    permission_classes = [IsAuthenticated]
    query_service = RoutineQueryService()

    def get(self, request):
        caregiver = Caregiver.objects.get(user=request.user)
        elderly_id = request.query_params.get("elderly_id")

        if not elderly_id:
            return Response({"detail": "elderly_id es requerido."}, status=400)

        elderly = get_object_or_404(Elderly, id=elderly_id, caregiver=caregiver)
        payload = self.query_service.get_daily_assignment_summary(elderly)
        serializer = DailyAssignmentSummarySerializer(payload)
        return Response(serializer.data)
