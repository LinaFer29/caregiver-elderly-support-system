#pragma once

#include <Arduino.h>

// TTP223B digital touch sensor used to trigger the voice response capture.
class TouchSensor {
 public:
  void begin();
  bool isPressed() const;
  // Waits for a fresh touch (the sensor must be released first).
  bool waitForPress(uint32_t timeoutMs);
};
