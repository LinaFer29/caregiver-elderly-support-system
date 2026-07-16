"""URL configuration for the voice assistant module."""

from django.urls import path

from .views import VoiceReminderListView


urlpatterns = [
    path("reminders", VoiceReminderListView.as_view(), name="voice-reminders"),
]
