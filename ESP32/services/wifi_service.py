"""WiFi connectivity service for the ESP32 MicroPython application."""
import network
import time

from config import WIFI_PASSWORD, WIFI_SSID, WIFI_TIMEOUT_SECONDS

class WiFiService:
    """Encapsulate WiFi connection management for station mode."""

    def __init__(
        self,
        ssid=WIFI_SSID,
        password=WIFI_PASSWORD,
        timeout_seconds=WIFI_TIMEOUT_SECONDS,
    ):
        """Initialize the service with WiFi credentials and timeout."""

        self._ssid = ssid
        self._password = password
        self._timeout_seconds = timeout_seconds
        self._wlan = network.WLAN(network.STA_IF)

    def connect(self):
        """Connect the ESP32 to the configured WiFi network."""

        self._reset_station_interface()

        if self._safe_is_connected():
            print("WiFi ya conectado.")
            print("IP asignada:", self.ip_address())
            return

        print("Conectando a WiFi...")

        try:
            self._wlan.connect(self._ssid, self._password)
        except OSError as exc:
            if not self._is_internal_state_error(exc):
                raise

            print("WiFi en estado interno inválido. Reiniciando interfaz STA...")
            self._recover_station_interface()
            self._wlan.connect(self._ssid, self._password)

        start_time = time.time()

        while not self._safe_is_connected():
            elapsed = time.time() - start_time
            status_text = self._status_text()

            if self._has_failed_status():
                print("\nError WiFi:", status_text)
                return

            if elapsed >= self._timeout_seconds:
                print("\nError: no fue posible conectar a la red WiFi.")
                print("Estado final WiFi:", status_text)
                return

            print(".", end="")
            time.sleep(1)

        print("\nWiFi conectado correctamente.")
        print("IP asignada:", self.ip_address())

    def is_connected(self):
        """Return whether the WiFi station interface is connected."""

        return self._safe_is_connected()

    def ip_address(self):
        """Return the assigned IPv4 address when connected."""

        if not self.is_connected():
            return None

        return self._wlan.ifconfig()[0]

    def get_mac_address(self):
        """Return the STA interface MAC address as an uppercase string."""

        mac_bytes = self._wlan.config("mac")
        return ":".join("{:02X}".format(byte) for byte in mac_bytes)

    def _reset_station_interface(self):
        """Reset the STA interface before each connection attempt."""

        self._recover_station_interface()

        try:
            self._wlan.disconnect()
        except Exception:
            pass

        time.sleep_ms(200)

    def _recover_station_interface(self):
        """Reset the STA interface to recover from MicroPython state issues."""

        try:
            self._wlan.disconnect()
        except Exception:
            pass

        try:
            self._wlan.active(False)
        except Exception:
            pass

        time.sleep_ms(300)
        self._wlan = network.WLAN(network.STA_IF)
        self._wlan.active(True)
        time.sleep_ms(300)

    def _safe_is_connected(self):
        """Return the connection status while tolerating transient STA errors."""

        try:
            return self._wlan.isconnected()
        except OSError as exc:
            if not self._is_internal_state_error(exc):
                raise

            self._recover_station_interface()
            return False

    def _is_internal_state_error(self, exc):
        """Identify the common MicroPython WiFi internal state error."""

        return "Internal State Error" in str(exc)

    def _status_value(self):
        """Return the current STA status code when available."""

        try:
            return self._wlan.status()
        except Exception:
            return None

    def _has_failed_status(self):
        """Return whether the STA status indicates a terminal failure."""

        return self._status_value() in (-1, -2, -3)

    def _status_text(self):
        """Return a human-readable description of the current WiFi status."""

        status = self._status_value()
        status_map = {
            None: "desconocido",
            1000: "conectado",
            0: "idle",
            1: "conectando",
            -1: "fallo de asociación",
            -2: "red no encontrada",
            -3: "contraseña incorrecta",
        }

        return "{} ({})".format(status_map.get(status, "estado no reconocido"), status)
