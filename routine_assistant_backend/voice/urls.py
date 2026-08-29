"""URL configuration for the voice assistant module."""

from django.urls import path

from .views import (
    VoiceAudioDownloadView,
    VoiceReminderListView,
    VoiceSTTView,
)


urlpatterns = [
    path("reminders", VoiceReminderListView.as_view(), name="voice-reminders"),
    path("assistant/stt/", VoiceSTTView.as_view(), name="voice-stt"),
    path(
        "assistant/audio/<str:file_name>/",
        VoiceAudioDownloadView.as_view(),
        name="voice-audio-download",
    ),
]
