from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializers import (
    CaregiverSerializer,
    DeviceAssociationSerializer,
    ElderlySerializer,
    UserRegisterSerializer,
)
from .models import Caregiver, Device, Elderly, User
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

        # Priorizamos username porque es unico y evita ambiguedades cuando
        # existen varios usuarios con el mismo correo historico.
        user = User.objects.filter(username__iexact=identifier).first()

        if not user:
            users_by_email = User.objects.filter(email__iexact=identifier).order_by("id")

            if users_by_email.count() > 1:
                return Response(
                    {"detail": "Se encontraron varias cuentas con ese correo. Inicia sesion con tu nombre de usuario."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = users_by_email.first()

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


class DeviceAssociationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DeviceAssociationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caregiver = Caregiver.objects.get(user=request.user)
        elderly = Elderly.objects.filter(
            id=serializer.validated_data["elderly_id"],
            caregiver=caregiver,
        ).first()

        if not elderly:
            return Response(
                {"detail": "El adulto mayor no pertenece al cuidador autenticado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if hasattr(elderly, "device"):
            return Response(
                {"detail": "El adulto mayor ya tiene un dispositivo asociado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device = Device.objects.filter(
            serial_number__iexact=serializer.validated_data["serial_number"]
        ).first()

        if not device:
            return Response(
                {"detail": "No existe un dispositivo con el número de serie indicado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if device.elderly_id is not None:
            return Response(
                {"detail": "El dispositivo ya está asociado a otro adulto mayor."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device.name = serializer.validated_data["name"]
        device.elderly = elderly
        device.status = "assigned"
        device.save(update_fields=["name", "elderly", "status"])

        return Response(
            {
                "message": "Dispositivo vinculado correctamente.",
                "device": {
                    "id": device.id,
                    "name": device.name,
                    "serial_number": device.serial_number,
                    "mac_address": device.mac_address,
                    "model": device.model,
                    "status": device.status,
                    "elderly_id": elderly.id,
                },
            },
            status=status.HTTP_200_OK,
        )
