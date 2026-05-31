from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializers import CaregiverSerializer, ElderlySerializer, UserRegisterSerializer
from .models import Caregiver, Elderly, User
from django.db.models import Q
from rest_framework_simplejwt.tokens import RefreshToken


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
            "email": request.user.email,
            "role": request.user.role
        })


class CustomLoginView(APIView):
    def post(self, request):
        identifier = (
            request.data.get("identifier")
            or request.data.get("username")
            or request.data.get("email")
            or ""
        )
        identifier = str(identifier).strip()
        password = request.data.get("password", "")

        if not identifier or not password:
            return Response(
                {"detail": "Usuario/email y contraseña son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        ).first()

        if not user:
            return Response(
                {"detail": "No se encontraron coincidencias para el usuario ingresado."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not user.check_password(password):
            return Response(
                {"detail": "Usuario o contraseña incorrectos."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_200_OK
        )
