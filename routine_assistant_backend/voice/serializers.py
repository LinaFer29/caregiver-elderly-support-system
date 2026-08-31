"""Serializers dedicated to the voice assistant module."""

from rest_framework import serializers


class VoiceReminderSerializer(serializers.Serializer):
    """Serializer for the voice reminder response payload."""

    assignment_id = serializers.IntegerField()
    elderly_id = serializers.IntegerField()
    activity = serializers.CharField()
    message = serializers.CharField()
    scheduled_time = serializers.TimeField()
    audio_file = serializers.CharField(allow_null=True)


class VoiceSTTRequestSerializer(serializers.Serializer):
    """Validate multipart audio plus assignment metadata."""

    audio = serializers.FileField()
    assignment_id = serializers.IntegerField(min_value=1)
    mac_address = serializers.CharField()
    sample_rate = serializers.IntegerField(required=False, min_value=1)

    def validate_mac_address(self, value):
        normalized = str(value or "").strip()
        if not normalized:
            raise serializers.ValidationError("mac_address es obligatorio.")
        return normalized


class VoiceSTTMetadataSerializer(serializers.Serializer):
    """Validate assignment metadata for octet-stream audio uploads."""

    assignment_id = serializers.IntegerField(min_value=1)
    mac_address = serializers.CharField()
    sample_rate = serializers.IntegerField(required=False, min_value=1)

    def validate_mac_address(self, value):
        normalized = str(value or "").strip()
        if not normalized:
            raise serializers.ValidationError("mac_address es obligatorio.")
        return normalized


class VoiceSTTResponseSerializer(serializers.Serializer):
    """Serializer for definitive spoken-response processing results."""

    audio_received = serializers.BooleanField()
    stt_success = serializers.BooleanField()
    transcription = serializers.CharField()
    normalized_transcription = serializers.CharField()
    was_interpreted = serializers.BooleanField()
    result = serializers.CharField()
    assignment_id = serializers.IntegerField()
    assignment_status = serializers.CharField()
    assignment_updated = serializers.BooleanField()
