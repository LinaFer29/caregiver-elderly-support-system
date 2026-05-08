from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializers import CaregiverSerializer, ElderlySerializer, UserRegisterSerializer
from .models import Caregiver, Elderly


# Create your views here.
class RegisterUserView(APIView):
    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Usuario creado correctamente"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class CaregiverViewSet(viewsets.ModelViewSet):
    queryset = Caregiver.objects.all()
    serializer_class = CaregiverSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Caregiver.objects.filter(user=self.request.user)

class ElderlyViewSet(viewsets.ModelViewSet):
    queryset = Elderly.objects.all()
    serializer_class = ElderlySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Elderly.objects.filter(caregiver__user=self.request.user)
    
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "id": request.user.id,
            "username": request.user.username,
            "role": request.user.role
        })