"""MQTT communication service for the ESP32 MicroPython application."""

import gc
import json
import time


from config import (
    DEBUG_MEMORY,
    MQTT_BROKER,
    MQTT_KEEPALIVE,
    MQTT_PASSWORD,
    MQTT_PORT,
    MQTT_RECONNECT_DELAY,
    MQTT_TOPIC_PREFIX,
    MQTT_TOPIC_SUFFIX,
    MQTT_USER,
    MQTT_USE_TLS,
)

try:
    from umqtt.simple import MQTTClient
except ImportError:
    MQTTClient = None


def log_memory(label):
    """Print heap diagnostics, including fragmentation details when available."""

    gc.collect()
    if DEBUG_MEMORY:
        print("{}: {}".format(label, gc.mem_free()))


class MQTTService:
    """Encapsulate MQTT connection, subscription and message handling."""

    def __init__(
        self,
        broker=MQTT_BROKER,
        port=MQTT_PORT,
        user=MQTT_USER,
        password=MQTT_PASSWORD,
        keepalive=MQTT_KEEPALIVE,
        use_tls=MQTT_USE_TLS,
        reconnect_delay=MQTT_RECONNECT_DELAY,
        topic_prefix=MQTT_TOPIC_PREFIX,
        topic_suffix=MQTT_TOPIC_SUFFIX,
    ):
        self._broker = broker
        self._port = port
        self._user = user
        self._password = password
        self._keepalive = keepalive
        self._use_tls = use_tls
        self._reconnect_delay = reconnect_delay
        self._topic_prefix = topic_prefix
        self._topic_suffix = topic_suffix
        self._client = None
        self._topic = None
        self._mac_address = None
        self._client_id = None
        self._pending_activity = None
        self._ssl_context = None

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

        print("")
        print("=== MQTT DEBUG ===")
        log_memory("Heap libre antes de MQTT")
        print("Broker:", self._broker)
        print("Puerto:", self._port)
        print("Client ID:", self._client_id)
        print("TLS:", self._use_tls)

        print("Construyendo cliente MQTT...")
        client = self._build_client()

        log_memory("Heap libre antes de connect()")

        client.set_callback(self._on_message)
        
        log_memory("Heap inmediatamente antes de TLS/MQTT")

        print("Ejecutando MQTT connect...")

        try:
            try:
                result = client.connect(timeout=10)
            except TypeError:
                result = client.connect()
            print("CONNECT MQTT terminado:", result)
        except Exception as exc:
            print("ERROR EN MQTT CONNECT:", type(exc).__name__, repr(exc))
            raise

        print("Suscribiendo a:", self._topic)

        client.subscribe(self._topic)

        self._client = client

        print("MQTT conectado")
        print("Suscrito a:", self._topic)
        log_memory("Heap después MQTT connect")

    def _to_bytes(self, value):
        if value is None or isinstance(value, bytes):
            return value
        return str(value).encode()
    
    def _build_client(self):
        """Build MQTT client with optional TLS."""

        kwargs = {
            "client_id": self._to_bytes(self._client_id),
            "server": self._broker,
            "port": self._port,
            "user": self._to_bytes(self._user),
            "password": self._to_bytes(self._password),
            "keepalive": self._keepalive,
        }

        if not self._use_tls:
            return MQTTClient(**kwargs)

        print("Configurando MQTT TLS...")

        import ssl

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.verify_mode = ssl.CERT_NONE
        self._ssl_context = ctx

        return MQTTClient(
            ssl=ctx,
            **kwargs
        )
    
    def publish(self, topic, payload, retain=False, qos=0):
        """Publish a message using the active MQTT connection."""

        if self._client is None:
            raise RuntimeError("MQTT no está conectado.")

        self._client.publish(topic, payload, retain=retain, qos=qos)

    def wait_for_activity(self, mac_address):
        """Wait for one MQTT activity payload and close the broker connection."""

        while True:
            try:
                self._pending_activity = None
                self.connect(mac_address)
                print("Esperando actividad MQTT...")

                while self._pending_activity is None:
                    self._client.wait_msg()

                payload = self._pending_activity
                print("Actividad MQTT recibida. Cerrando MQTT antes de HTTPS/audio.")
                return payload

            except Exception as exc:
                print(
                    "Conexión MQTT perdida:",
                    type(exc).__name__,
                    repr(exc)
                )
                print(
                    "Reintentando conexión MQTT en {} segundos...".format(
                        self._reconnect_delay
                    )
                )
            finally:
                self._pending_activity = None
                self._close_client()
                self._ssl_context = None
                gc.collect()

            if self._pending_activity is None:
                time.sleep(self._reconnect_delay)

    def _on_message(self, topic, payload):
        """Decode the MQTT message and store activity payloads for later work."""

        topic_text = self._decode_bytes(topic)
        payload_text = self._decode_bytes(payload)

        print("")
        print("MQTT mensaje recibido")
        print("Topic:", topic_text)
        print("Payload:", payload_text)
        log_memory("Heap al recibir actividad")

        try:
            payload_json = json.loads(payload_text)
        except Exception:
            return

        if isinstance(payload_json, dict):
            if payload_json.get("type") == "activity":
                self._pending_activity = payload_json
                print("Actividad pendiente almacenada.")
                return

            for key, value in payload_json.items():
                print("{}: {}".format(key, value))

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
        """Close the current MQTT client and release TLS/socket references."""

        if self._client is None:
            gc.collect()
            return

        client = self._client
        self._client = None

        try:
            client.disconnect()
        except Exception:
            pass

        for attr in ("sock", "_sock", "socket", "_socket"):
            try:
                sock = getattr(client, attr, None)
                if sock is not None:
                    sock.close()
            except Exception:
                pass

        del client
        gc.collect()

    def close(self):
        """Public cleanup hook used by the main state machine."""

        self._close_client()
        self._ssl_context = None
        gc.collect()
