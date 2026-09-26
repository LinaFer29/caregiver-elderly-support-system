#pragma once

#include <Arduino.h>

#include "config.h"

// Wi-Fi station connection and device MAC address.
class WifiService {
 public:
  bool connect(uint32_t timeoutMs = WIFI_TIMEOUT_MS);
  void ensureConnected();
  bool isConnected() const;
  String getMacAddress() const;
};
