"""Celery tasks for the voice assistant module."""

from celery import shared_task

from .services.mqtt_service import VoiceMQTTPublisherService
from .services.reminder_service import ReminderService
from .services.voice_assistant_service import VoiceAssistantService


@shared_task(name="voice.tasks.dispatch_due_assignments")
def dispatch_due_assignments():
    """Publish MQTT notifications for assignments due in the current minute."""

    reminder_service = ReminderService()
    voice_assistant_service = VoiceAssistantService(
        reminder_service=reminder_service,
    )
    mqtt_service = VoiceMQTTPublisherService()

    published_count = 0

    for assignment in reminder_service.get_assignments_due_for_dispatch():
        device = reminder_service.get_device_for_elderly(assignment.elderly)

        if device is None or not device.mac_address:
            continue

        reminder_payload = voice_assistant_service.build_due_reminder_payload(
            assignment
        )
        mqtt_service.publish_reminder(device.mac_address, reminder_payload)
        published_count += 1

    return published_count
