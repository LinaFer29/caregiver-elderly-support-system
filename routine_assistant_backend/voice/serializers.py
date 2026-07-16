"""Serializers dedicated to the voice assistant module."""

from rest_framework import serializers


class VoiceReminderSerializer(serializers.Serializer):
    """Serializer for the voice reminder response payload."""

    assignment_id = serializers.IntegerField()
    elderly_id = serializers.IntegerField()
    activity = serializers.CharField()
    message = serializers.CharField()
    scheduled_time = serializers.TimeField()
