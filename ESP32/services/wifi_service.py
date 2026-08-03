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

        if not self._wlan.active():
            self._wlan.active(True)

        if self._wlan.isconnected():
            print("WiFi ya conectado.")
            print("IP asignada:", self.ip_address())
            return

        print("Conectando a WiFi...")
        self._wlan.connect(self._ssid, self._password)

        start_time = time.time()

        while not self._wlan.isconnected():
            elapsed = time.time() - start_time
            if elapsed >= self._timeout_seconds:
                print("\nError: no fue posible conectar a la red WiFi.")
                return

            print(".", end="")
            time.sleep(1)

        print("\nWiFi conectado correctamente.")
        print("IP asignada:", self.ip_address())

    def is_connected(self):
        """Return whether the WiFi station interface is connected."""

        return self._wlan.isconnected()

    def ip_address(self):
        """Return the assigned IPv4 address when connected."""

        if not self.is_connected():
            return None

        return self._wlan.ifconfig()[0]

    def get_mac_address(self):
        """Return the STA interface MAC address as an uppercase string."""

        mac_bytes = self._wlan.config("mac")
        return ":".join("{:02X}".format(byte) for byte in mac_bytes)
