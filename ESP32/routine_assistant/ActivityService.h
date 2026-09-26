#pragma once

#include <Arduino.h>

#include "Activity.h"
#include "BluetoothPlayer.h"
#include "HttpService.h"
#include "Microphone.h"
#include "TouchSensor.h"

// Orchestrates one activity: download reminder -> play over Bluetooth ->
// wait for touch -> record response -> submit to STT -> print result.
class ActivityService {
 public:
  ActivityService(HttpService& http, BluetoothPlayer& player, Microphone& microphone,
                  TouchSensor& touch);

  bool process(const Activity& activity, const String& macAddress);

 private:
  bool playReminderAndWaitForTouch();
  void playFeedbackTones(uint8_t count);
  void printActivity(const Activity& activity);
  void printResult(const SttResult& result, const CaptureInfo& capture);
  void cleanupFiles();

  HttpService& _http;
  BluetoothPlayer& _player;
  Microphone& _microphone;
  TouchSensor& _touch;
};
