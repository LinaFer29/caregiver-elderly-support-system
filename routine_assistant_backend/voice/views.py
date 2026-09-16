"""Views dedicated to the voice assistant module."""

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.exceptions import ParseError, ValidationError as DRFValidationError
from rest_framework.parsers import BaseParser, FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .constants import DEFAULT_AUDIO_SAMPLE_RATE
from .serializers import (
    VoiceReminderSerializer,
    VoiceSTTMetadataSerializer,
    VoiceSTTRequestSerializer,
    VoiceSTTResponseSerializer,
)
from .services.response_service import ResponseService
from .services.voice_assistant_service import VoiceAssistantService


class OctetStreamAudioParser(BaseParser):
    """Parse raw PCM16 bytes sent as application/octet-stream."""

    media_type = "application/octet-stream"
    chunk_size = 4096

    def parse(self, stream, media_type=None, parser_context=None):
        request = (parser_context or {}).get("request")
        content_length = getattr(request, "META", {}).get("CONTENT_LENGTH")

        try:
            expected_length = int(content_length)
        except (TypeError, ValueError):
            raise ParseError("Content-Length es obligatorio para audio PCM16.")

        if expected_length <= 0:
            raise ParseError("Content-Length debe ser mayor que cero.")

        print("STT body expected={}".format(expected_length), flush=True)

        received = bytearray()

        while len(received) < expected_length:
            remaining = expected_length - len(received)
            chunk = stream.read(min(self.chunk_size, remaining))

            if not chunk:
                break

            received.extend(chunk)

        received_length = len(received)
        print("STT body received={}".format(received_length), flush=True)

        if received_length != expected_length:
            print(
                "STT body incomplete expected={} received={}".format(
                    expected_length,
                    received_length,
                ),
                flush=True,
            )
            raise ParseError(
                "Audio PCM16 incompleto: esperados {} bytes, recibidos {}.".format(
                    expected_length,
                    received_length,
                )
            )

        print("STT body complete bytes={}".format(received_length), flush=True)
        return {"audio_bytes": bytes(received)}


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
                metadata_serializer = VoiceSTTMetadataSerializer(
                    data=request.query_params,
                )
                metadata_serializer.is_valid(raise_exception=True)
                metadata = metadata_serializer.validated_data

                result = service.process_assignment_response_stream(
                    audio_bytes=request.data.get("audio_bytes", b""),
                    mac_address=metadata["mac_address"],
                    assignment_id=metadata["assignment_id"],
                    sample_rate=metadata.get(
                        "sample_rate",
                        DEFAULT_AUDIO_SAMPLE_RATE,
                    ),
                )
            else:
                serializer = VoiceSTTRequestSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                result = service.process_assignment_response_file(
                    audio_file=serializer.validated_data["audio"],
                    mac_address=serializer.validated_data["mac_address"],
                    assignment_id=serializer.validated_data["assignment_id"],
                    sample_rate=serializer.validated_data.get("sample_rate"),
                )
        except (DRFValidationError, DjangoValidationError) as exc:
            detail = exc.detail if hasattr(exc, "detail") else str(exc)
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = VoiceSTTResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

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
