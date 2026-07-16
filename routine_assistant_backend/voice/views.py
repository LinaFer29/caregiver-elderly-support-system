"""Views dedicated to the voice assistant module."""

from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import VoiceReminderSerializer
from .services.voice_assistant_service import VoiceAssistantService


class VoiceReminderListView(APIView):
    """Expose due reminders for the voice assistant device."""

    def get(self, request):
        elderly_id_param = request.query_params.get("elderly_id")

        if elderly_id_param is None:
            return Response(
                {"detail": "El parámetro elderly_id es obligatorio."},
                status=400,
            )

        try:
            elderly_id = int(elderly_id_param)
            if elderly_id <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {"detail": "elderly_id debe ser un número entero válido."},
                status=400,
            )

        service = VoiceAssistantService()
        reminders = service.get_due_reminders(elderly_id)
        serializer = VoiceReminderSerializer(reminders, many=True)
        return Response(serializer.data)
