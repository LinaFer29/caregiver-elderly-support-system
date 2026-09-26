#pragma once

#include <Arduino.h>
#include <WiFi.h>

#include "Activity.h"

// Minimal HTTP client for the backend: reminder download and STT submission.
class HttpService {
 public:
  bool downloadAudio(const String& audioFile, const char* destinationPath);
  bool submitResponseFile(const String& macAddress, long assignmentId, uint32_t sampleRate,
                          const char* pcmPath, SttResult& result);

 private:
  struct ResponseHead {
    String statusLine;
    int statusCode = 0;
    long contentLength = -1;
    bool chunked = false;
  };

  bool openConnection(WiFiClient& client);
  bool writeAll(WiFiClient& client, const uint8_t* data, size_t length);
  bool writeText(WiFiClient& client, const String& text);
  bool readLine(WiFiClient& client, String& line, uint32_t deadline);
  bool readResponseHead(WiFiClient& client, uint32_t deadline, ResponseHead& head);
  bool readExact(WiFiClient& client, size_t count, String& output, uint32_t deadline);
  bool readSmallBody(WiFiClient& client, const ResponseHead& head, String& body, uint32_t deadline);

  static String buildAuthority();
  static String encodeQueryValue(const String& value);
};
