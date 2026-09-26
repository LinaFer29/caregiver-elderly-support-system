#pragma once

#include <Arduino.h>

// Activity payload received through MQTT (type == "activity").
struct Activity {
  long assignmentId = 0;
  String activity;
  String message;
  String audioFile;
  String scheduledTime;
};

// Result returned by the backend STT endpoint.
struct SttResult {
  long assignmentId = 0;
  String transcription;
  String result;
  String assignmentStatus;
  bool assignmentUpdated = false;
};

// Metadata of one microphone capture.
struct CaptureInfo {
  uint32_t bytesWritten = 0;
  int32_t peakPcm16 = 0;
  uint32_t sampleRate = 0;
};
