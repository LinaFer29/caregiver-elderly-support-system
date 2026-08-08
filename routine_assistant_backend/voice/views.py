"""Views dedicated to the voice assistant module."""

from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import BaseParser, FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .constants import DEFAULT_AUDIO_SAMPLE_RATE
from .serializers import (
    VoiceReminderSerializer,
    VoiceSTTRequestSerializer,
    VoiceSTTResponseSerializer,
)
from .services.response_service import ResponseService
from .services.voice_assistant_service import VoiceAssistantService


class OctetStreamAudioParser(BaseParser):
    """Parse raw PCM16 bytes sent as application/octet-stream."""

    media_type = "application/octet-stream"

    def parse(self, stream, media_type=None, parser_context=None):
        return {"audio_bytes": stream.read()}


class VoiceReminderListView(APIView):
    """Expose due reminders for the voice assistant device."""

    def get(self, request):
        mac_address = request.query_params.get("mac_address")

        if mac_address is None or not str(mac_address).strip():
            return Response(
                {"detail": "El parámetro mac_address es obligatorio."},
                status=400,
            )

        service = VoiceAssistantService()
        reminders = service.get_due_reminders(mac_address)
        serializer = VoiceReminderSerializer(reminders, many=True)
        return Response(serializer.data)


class VoiceSTTView(APIView):
    """Receive audio from the assistant device and resolve a response."""

    parser_classes = [MultiPartParser, FormParser, OctetStreamAudioParser]

    def post(self, request):
        service = VoiceAssistantService()

        try:
            if request.content_type == "application/octet-stream":
                result = service.process_pcm16_command(
                    audio_bytes=request.data.get("audio_bytes", b""),
                    sample_rate=DEFAULT_AUDIO_SAMPLE_RATE,
                )
            else:
                serializer = VoiceSTTRequestSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                result = service.process_speech_command(
                    audio_file=serializer.validated_data["audio"],
                    sample_rate=serializer.validated_data.get("sample_rate"),
                )
        except ValidationError as exc:
            detail = exc.detail if hasattr(exc, "detail") else str(exc)
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = VoiceSTTResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


# class VoiceAudioDownloadView(APIView):
#     """Serve assistant response audio files from the configured media folder."""

#     response_service = ResponseService()

#     def get(self, request, file_name):
#         if "/" in file_name or "\\" in file_name:
#             raise Http404("Archivo no encontrado.")

#         file_path = self.response_service.get_audio_path(file_name).resolve()
#         audio_root = (settings.MEDIA_ROOT / "assistant_audio").resolve()

#         if audio_root not in file_path.parents:
#             raise Http404("Archivo no encontrado.")

#         if not file_path.is_file():
#             raise Http404("Archivo no encontrado.")

#         return FileResponse(file_path.open("rb"), content_type="audio/wav")

class VoiceAudioDownloadView(APIView):
    """Serve assistant response audio files from the configured media folder."""

    response_service = ResponseService()

    def get(self, request, file_name):
        if "/" in file_name or "\\" in file_name:
            raise Http404("Archivo no encontrado.")

        file_path = self.response_service.get_audio_path(file_name).resolve()
        audio_root = (
            settings.MEDIA_ROOT / "assistant_audio"
        ).resolve()

        if audio_root not in file_path.parents:
            raise Http404("Archivo no encontrado.")

        if not file_path.is_file():
            raise Http404("Archivo no encontrado.")

        audio_file = file_path.open("rb")

        response = FileResponse(
            audio_file,
            content_type="audio/wav",
            as_attachment=False,
            filename=file_name,
        )

        response["Content-Length"] = str(
            file_path.stat().st_size
        )

        return response
