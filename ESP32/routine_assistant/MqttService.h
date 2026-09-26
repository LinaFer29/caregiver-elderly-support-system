#pragma once

#include <Arduino.h>
#include <PubSubClient.h>
#include <WiFi.h>

#include "Activity.h"
#include "WifiService.h"
#include "config.h"

// MQTT subscription to device/<device_id>/audio and activity decoding.
class MqttService {
 public:
  explicit MqttService(WifiService& wifi);

  // Blocks until one valid activity payload arrives (reconnects as needed).
  bool waitForActivity(const String& macAddress, Activity& activity);
  void disconnect();

 private:
  bool connect(const String& macAddress);
  bool parseActivity(const char* payload, size_t length, Activity& activity);
  void storePayload(const char* topic, const uint8_t* payload, unsigned int length);

  static String buildDeviceId(const String& macAddress);
  static void onMessage(char* topic, uint8_t* payload, unsigned int length);

  static MqttService* _instance;

  WifiService& _wifi;
  WiFiClient _network;
  PubSubClient _client;
  String _clientId;
  String _topic;
  char _payload[MQTT_BUFFER_BYTES + 1];
  size_t _payloadLength = 0;
  bool _hasPayload = false;
};
