#include "MqttService.h"

#include <ArduinoJson.h>

MqttService* MqttService::_instance = nullptr;

namespace {

const char* firstString(JsonVariantConst primary, JsonVariantConst fallback) {
  if (primary.is<const char*>()) {
    return primary.as<const char*>();
  }
  if (fallback.is<const char*>()) {
    return fallback.as<const char*>();
  }
  return "";
}

}  // namespace

MqttService::MqttService(WifiService& wifi) : _wifi(wifi), _client(_network) {
  _instance = this;
}

String MqttService::buildDeviceId(const String& macAddress) {
  String deviceId = macAddress;
  deviceId.replace(":", "");
  deviceId.trim();
  deviceId.toLowerCase();
  return deviceId;
}

bool MqttService::connect(const String& macAddress) {
  _clientId = buildDeviceId(macAddress);
  _topic = String(MQTT_TOPIC_PREFIX) + "/" + _clientId + "/" + MQTT_TOPIC_SUFFIX;

  _client.setServer(MQTT_BROKER, MQTT_PORT);
  _client.setCallback(onMessage);
  _client.setBufferSize(MQTT_BUFFER_BYTES);
  _client.setKeepAlive(MQTT_KEEPALIVE_SECONDS);
  _client.setSocketTimeout(10);

  Serial.println();
  Serial.println("=== MQTT ===");
  Serial.printf("Broker: %s:%u\n", MQTT_BROKER, MQTT_PORT);
  Serial.printf("Client ID: %s\n", _clientId.c_str());
  Serial.print("IP del ESP32: ");
  Serial.print(WiFi.localIP());
  Serial.printf(" | RSSI: %d dBm | Heap libre: %lu bytes\n", WiFi.RSSI(),
                (unsigned long)ESP.getFreeHeap());

  // Open the TCP socket ourselves with a generous timeout: while A2DP streams,
  // Wi-Fi shares the radio with Bluetooth and the library's default connect
  // timeout (~3 s) can expire. PubSubClient reuses an already connected client.
  _network.stop();
  if (!_network.connect(MQTT_BROKER, MQTT_PORT, MQTT_CONNECT_TIMEOUT_MS)) {
    Serial.printf("Error TCP: el broker %s:%u no respondió en %lu ms.\n", MQTT_BROKER, MQTT_PORT,
                  (unsigned long)MQTT_CONNECT_TIMEOUT_MS);
    return false;
  }
  Serial.println("Conexión TCP con el broker establecida.");

  if (!_client.connect(_clientId.c_str(), MQTT_USER, MQTT_PASSWORD)) {
    Serial.printf("Error en MQTT connect. Estado: %d\n", _client.state());
    return false;
  }

  if (!_client.subscribe(_topic.c_str())) {
    Serial.printf("Error al suscribirse a %s\n", _topic.c_str());
    _client.disconnect();
    return false;
  }

  Serial.printf("MQTT conectado. Suscrito a: %s\n", _topic.c_str());
  return true;
}

bool MqttService::waitForActivity(const String& macAddress, Activity& activity) {
  _hasPayload = false;

  while (true) {
    _wifi.ensureConnected();

    if (!_client.connected()) {
      if (!connect(macAddress)) {
        Serial.printf("Reintentando conexión MQTT en %lu ms...\n",
                      (unsigned long)MQTT_RECONNECT_DELAY_MS);
        delay(MQTT_RECONNECT_DELAY_MS);
        continue;
      }
      Serial.println("Esperando actividad MQTT...");
    }

    _client.loop();

    if (_hasPayload) {
      _hasPayload = false;
      if (parseActivity(_payload, _payloadLength, activity)) {
        return true;
      }
    }

    delay(10);
  }
}

void MqttService::disconnect() {
  if (_client.connected()) {
    _client.disconnect();
  }
  _network.stop();
}

void MqttService::onMessage(char* topic, uint8_t* payload, unsigned int length) {
  if (_instance != nullptr) {
    _instance->storePayload(topic, payload, length);
  }
}

void MqttService::storePayload(const char* topic, const uint8_t* payload, unsigned int length) {
  Serial.println();
  Serial.println("MQTT mensaje recibido");
  Serial.printf("Topic: %s\n", topic);

  if (length > MQTT_BUFFER_BYTES) {
    Serial.printf("Error: payload de %u bytes supera el buffer.\n", length);
    return;
  }

  memcpy(_payload, payload, length);
  _payload[length] = '\0';
  _payloadLength = length;
  _hasPayload = true;

  Serial.printf("Payload: %s\n", _payload);
}

bool MqttService::parseActivity(const char* payload, size_t length, Activity& activity) {
  JsonDocument doc;
  const DeserializationError error = deserializeJson(doc, payload, length);

  if (error) {
    Serial.printf("Error: payload MQTT no es JSON válido (%s).\n", error.c_str());
    return false;
  }

  const char* type = doc["type"] | "";
  if (strcmp(type, "activity") != 0) {
    Serial.println("Mensaje MQTT ignorado (type distinto de \"activity\").");
    return false;
  }

  activity.assignmentId = doc["assignment_id"] | 0L;
  activity.audioFile = doc["audio_file"] | "";
  activity.activity = firstString(doc["activity"], doc["title"]);
  activity.message = firstString(doc["message"], doc["description"]);
  activity.scheduledTime = doc["scheduled_time"] | "";

  if (activity.audioFile.isEmpty()) {
    Serial.println("Error: el mensaje no contiene audio_file.");
    return false;
  }

  if (activity.assignmentId <= 0) {
    Serial.println("Error: el mensaje no contiene assignment_id.");
    return false;
  }

  return true;
}
