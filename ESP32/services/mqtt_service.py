"""MQTT communication service for the ESP32 MicroPython application."""

import json
import time

from models.reminder import Reminder
from services.audio_service import AudioService
from services.http_service import HttpService

from config import (
    MQTT_BROKER,
    MQTT_KEEPALIVE,
    MQTT_PASSWORD,
    MQTT_PORT,
    MQTT_RECONNECT_DELAY,
    MQTT_TOPIC_PREFIX,
    MQTT_TOPIC_SUFFIX,
    MQTT_USER,
)

try:
    from umqtt.simple import MQTTClient
except ImportError:
    MQTTClient = None


class MQTTService:
    """Encapsulate MQTT connection, subscription and message handling."""

    def __init__(
        self,
        broker=MQTT_BROKER,
        port=MQTT_PORT,
        user=MQTT_USER,
        password=MQTT_PASSWORD,
        keepalive=MQTT_KEEPALIVE,
        reconnect_delay=MQTT_RECONNECT_DELAY,
        topic_prefix=MQTT_TOPIC_PREFIX,
        topic_suffix=MQTT_TOPIC_SUFFIX,
        http_service=None,
        audio_service=None,
    ):
        self._broker = broker
        self._port = port
        self._user = user
        self._password = password
        self._keepalive = keepalive
        self._reconnect_delay = reconnect_delay
        self._topic_prefix = topic_prefix
        self._topic_suffix = topic_suffix
        self._http_service = http_service or HttpService()
        self._audio_service = audio_service or AudioService()
        self._client = None
        self._topic = None
        self._mac_address = None
        self._client_id = None

    def build_device_id(self, mac_address):
        """Build a stable MQTT device identifier from the ESP32 MAC address."""

        return (mac_address or "").replace(":", "").strip().lower()

    def build_topic(self, mac_address):
        """Build the device-specific MQTT topic using the MAC-derived identifier."""

        device_id = self.build_device_id(mac_address)
        return "{}/{}/{}".format(
            self._topic_prefix,
            device_id,
            self._topic_suffix,
        )

    def connect(self, mac_address):
        """Connect to the broker and subscribe to the device topic."""

        self._ensure_library_available()

        self._mac_address = mac_address
        self._client_id = self.build_device_id(mac_address)
        self._topic = self.build_topic(mac_address)

        print("Conectando MQTT...")
        client = MQTTClient(
            client_id=self._client_id,
            server=self._broker,
            port=self._port,
            user=self._user,
            password=self._password,
            keepalive=self._keepalive,
        )
        client.set_callback(self._on_message)
        client.connect()
        client.subscribe(self._topic)

        self._client = client
        print("MQTT conectado")
        print("Suscrito a:", self._topic)

    def publish(self, topic, payload, retain=False, qos=0):
        """Publish a message using the active MQTT connection."""

        if self._client is None:
            raise RuntimeError("MQTT no está conectado.")

        self._client.publish(topic, payload, retain=retain, qos=qos)

    def listen_forever(self, mac_address):
        """Keep the MQTT connection alive, reconnecting when necessary."""

        while True:
            try:
                if self._client is None:
                    self.connect(mac_address)
                    print("Esperando mensajes...")

                self._client.check_msg()
                time.sleep_ms(200)
            except Exception as exc:
                print("Conexión MQTT perdida:", exc)
                self._close_client()
                print(
                    "Reintentando conexión MQTT en {} segundos...".format(
                        self._reconnect_delay
                    )
                )
                time.sleep(self._reconnect_delay)

    def _on_message(self, topic, payload):
        """Handle an incoming MQTT message and print its contents."""

        topic_text = self._decode_bytes(topic)
        payload_text = self._decode_bytes(payload)

        print("")
        print("MQTT mensaje recibido")
        print("Topic:", topic_text)
        print("Payload:", payload_text)

        try:
            payload_json = json.loads(payload_text)
        except Exception:
            return

        if isinstance(payload_json, dict):
            if payload_json.get("type") == "activity":
                self._handle_activity_message(payload_json)

            for key, value in payload_json.items():
                print("{}: {}".format(key, value))

    def _handle_activity_message(self, payload_json):
        """Download and play the reminder audio referenced by the MQTT payload."""

        try:
            reminder = Reminder.from_dict(payload_json)
        except Exception as exc:
            print("Error al interpretar el payload MQTT como recordatorio:", exc)
            return

        print("")
        print("Actividad recibida:")
        print("ID assignment:", reminder.assignment_id)
        print("Actividad:", reminder.activity)
        print("Mensaje:", reminder.message)
        print("Audio:", reminder.audio_file)

        if not reminder.audio_file:
            print("Error: el mensaje MQTT no contiene audio_file.")
            return

        print("")
        print("Descargando audio del recordatorio...")
        wav_path = self._http_service.download_audio(reminder.audio_file)

        if not wav_path:
            print("No fue posible descargar el audio del recordatorio.")
            return

        try:
            print("Reproduciendo recordatorio...")
            self._audio_service.play_wav(wav_path)
            print("Reproducción terminada.")
        except Exception as exc:
            print("Error durante la reproducción del audio:", exc)

    def _decode_bytes(self, value):
        """Decode MQTT bytes to a printable string."""

        if isinstance(value, bytes):
            return value.decode("utf-8", "replace")
        return str(value)

    def _ensure_library_available(self):
        """Fail with a clear message when umqtt.simple is missing."""

        if MQTTClient is None:
            raise ImportError(
                "No se pudo importar umqtt.simple. "
                "Debes copiar la librería `umqtt/simple.py` al ESP32."
            )

    def _close_client(self):
        """Close the current MQTT client if it exists."""

        if self._client is None:
            return

        try:
            self._client.disconnect()
        except Exception:
            pass

        self._client = None
