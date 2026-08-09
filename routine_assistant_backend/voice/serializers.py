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
    """Validate the payload received from the voice assistant STT endpoint."""

    audio = serializers.FileField()
    sample_rate = serializers.IntegerField(required=False, min_value=1)


class VoiceSTTResponseSerializer(serializers.Serializer):
    """Serializer for the STT response returned to the assistant device."""

    transcription = serializers.CharField()
    intent = serializers.CharField(allow_null=True)
    response_text = serializers.CharField()
    audio_file = serializers.CharField(allow_null=True)
