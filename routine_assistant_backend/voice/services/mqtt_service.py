"""MQTT publishing services for the voice assistant module."""

import json
from datetime import time

from django.conf import settings

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None


class VoiceMQTTPublisherService:
    """Publish device-directed voice assistant messages through MQTT."""

    topic_prefix = "device"
    topic_suffix = "audio"

    def build_device_id(self, mac_address):
        """Normalize a MAC address to the device identifier used by the ESP32."""

        return (mac_address or "").replace(":", "").strip().lower()

    def build_topic(self, device_id):
        """Build the MQTT topic used by an ESP32 device."""

        return "{}/{}/{}".format(
            self.topic_prefix,
            device_id,
            self.topic_suffix,
        )

    def build_activity_payload(self, activity):
        """Build the JSON payload sent to the ESP32 for an activity."""

        return {
            "type": "activity",
            "activity_id": activity.id,
            "title": activity.title,
            "description": activity.description,
        }

    def build_reminder_payload(self, reminder_payload):
        """Build the JSON payload sent to the ESP32 for a due reminder."""

        payload = {
            "type": "activity",
            "assignment_id": reminder_payload.get("assignment_id"),
            "elderly_id": reminder_payload.get("elderly_id"),
            "activity": reminder_payload.get("activity"),
            "message": reminder_payload.get("message"),
            "scheduled_time": self._serialize_value(
                reminder_payload.get("scheduled_time")
            ),
            "audio_file": reminder_payload.get("audio_file"),
        }
        return payload

    def publish_activity(self, device_id, activity):
        """Publish an activity payload to the MQTT topic of a device."""

        payload = self.build_activity_payload(activity)
        return self._publish_payload(device_id, payload)

    def publish_reminder(self, mac_address, reminder_payload):
        """Publish a reminder payload to the MQTT topic of a device."""

        device_id = self.build_device_id(mac_address)
        payload = self.build_reminder_payload(reminder_payload)
        return self._publish_payload(device_id, payload)

    def _publish_payload(self, device_id, payload):
        """Publish a JSON payload to the MQTT topic of a device."""

        self._ensure_library_available()

        topic = self.build_topic(device_id)
        payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

        client = mqtt.Client()

        try:
            if settings.MQTT_USER:
                client.username_pw_set(
                    settings.MQTT_USER,
                    settings.MQTT_PASSWORD,
                )

            client.connect(
                settings.MQTT_BROKER,
                settings.MQTT_PORT,
                settings.MQTT_KEEPALIVE,
            )
            result = client.publish(topic, payload_json)

            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(
                    "No fue posible publicar la actividad en MQTT. Código: {}.".format(
                        result.rc
                    )
                )

            client.loop(timeout=1.0)
        finally:
            try:
                client.disconnect()
            except Exception:
                pass

        return {
            "topic": topic,
            "payload": payload,
        }

    def _ensure_library_available(self):
        """Fail with a clear error if paho-mqtt is not installed."""

        if mqtt is None:
            raise ImportError(
                "No se pudo importar paho-mqtt. "
                "Instala la dependencia `paho-mqtt` en el backend."
            )

    def _serialize_value(self, value):
        """Serialize reminder values to MQTT-friendly JSON scalars."""

        if isinstance(value, time):
            return value.isoformat()

        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except TypeError:
                return value

        return value
