#include "WifiService.h"

#include <WiFi.h>

bool WifiService::connect(uint32_t timeoutMs) {
  if (isConnected()) {
    return true;
  }

  WiFi.mode(WIFI_STA);
  // Modem sleep must stay enabled: the ESP32 aborts when Wi-Fi and
  // Bluetooth Classic run together with Wi-Fi sleep disabled.
  WiFi.setSleep(true);

  Serial.printf("Conectando a Wi-Fi \"%s\"...\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  const uint32_t start = millis();
  while (!isConnected()) {
    if (millis() - start >= timeoutMs) {
      Serial.println("No fue posible conectar a Wi-Fi.");
      WiFi.disconnect();
      return false;
    }
    delay(250);
  }

  Serial.print("Wi-Fi conectado. IP: ");
  Serial.println(WiFi.localIP());
  Serial.print("Gateway: ");
  Serial.print(WiFi.gatewayIP());
  Serial.print(" | Máscara: ");
  Serial.print(WiFi.subnetMask());
  Serial.printf(" | BSSID (punto de acceso): %s | Canal: %ld\n", WiFi.BSSIDstr().c_str(),
                (long)WiFi.channel());
  return true;
}

void WifiService::ensureConnected() {
  while (!connect()) {
    Serial.printf("Reintentando Wi-Fi en %lu ms...\n", (unsigned long)WIFI_RETRY_DELAY_MS);
    delay(WIFI_RETRY_DELAY_MS);
  }
}

bool WifiService::isConnected() const {
  return WiFi.status() == WL_CONNECTED;
}

String WifiService::getMacAddress() const {
  String mac = WiFi.macAddress();
  if (MAC_ADDRESS_LOWERCASE) {
    mac.toLowerCase();
  }
  return mac;
}
