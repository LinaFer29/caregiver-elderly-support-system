#include "TouchSensor.h"

#include "config.h"

void TouchSensor::begin() {
  pinMode(TOUCH_PIN, INPUT);
}

bool TouchSensor::isPressed() const {
  return digitalRead(TOUCH_PIN) == TOUCH_ACTIVE_LEVEL;
}

bool TouchSensor::waitForPress(uint32_t timeoutMs) {
  const uint32_t start = millis();

  // Ignore a finger that was already on the sensor: require a new touch.
  while (isPressed()) {
    if (millis() - start >= timeoutMs) {
      return false;
    }
    delay(10);
  }

  while (millis() - start < timeoutMs) {
    if (isPressed()) {
      delay(TOUCH_DEBOUNCE_MS);
      if (isPressed()) {
        Serial.println("Toque detectado.");
        return true;
      }
    }
    delay(10);
  }

  return false;
}
