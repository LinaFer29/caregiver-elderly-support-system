from django.shortcuts import get_object_or_404, render

from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from activities.models import Activity
from users.models import Caregiver
from .models import Assignment, Program
from .serializers import ActivityWithProgramSerializer, AssignmentSerializer, ProgramSerializer
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction


# Create your views here.
class ProgramViewSet(viewsets.ModelViewSet):
    queryset = Program.objects.all()
    serializer_class = ProgramSerializer
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        print("USER:", self.request.user)
        print("AUTH:", self.request.auth)
        return Program.objects.filter(
            caregiver__user=self.request.user
        )

    def perform_create(self, serializer):
        caregiver = get_object_or_404(Caregiver, user=self.request.user)
        serializer.save(caregiver=caregiver)

    def perform_update(self, serializer):
        caregiver = Caregiver.objects.get(user=self.request.user)
        serializer.save(caregiver=caregiver)
    

class AssigmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer


class ActivitiesWithProgramView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        caregiver = Caregiver.objects.get(user=request.user)

        programs = Program.objects.filter(
            caregiver=caregiver
        ).select_related('activity')

        activities = [program.activity for program in programs]

        serializer = ActivityWithProgramSerializer(
            activities,
            many=True
        )

        return Response(serializer.data)
    
    def post(self, request):
        caregiver = Caregiver.objects.get(user=request.user)

        # 1. Crear Activity
        activity = Activity.objects.create(
            title=request.data.get("title"),
            description=request.data.get("description"),
            category_id=request.data.get("category"),
        )

        # 2. Crear Program
        program = Program.objects.create(
            caregiver=caregiver,
            activity=activity,
            date=request.data.get("date"),
            time=request.data.get("time"),
            frequency=request.data.get("frequency"),
            is_active=request.data.get("is_active", False),
        )

        return Response({
            "activity_id": activity.id,
            "program_id": program.id
        }, status=status.HTTP_201_CREATED)
    
    def put(self, request, activity_id):
        caregiver = Caregiver.objects.get(user=request.user)

        # Obtener Activity asegurando que pertenece al usuario
        activity = get_object_or_404(
            Activity,
            id=activity_id,
            program__caregiver=caregiver
        )

        # Obtener Program asociado
        program = get_object_or_404(
            Program,
            activity=activity,
            caregiver=caregiver
        )

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

        return Response({
            "message": "Actividad actualizada correctamente"
        }, status=200)
