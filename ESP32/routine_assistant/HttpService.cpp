#include "HttpService.h"

#include <ArduinoJson.h>
#include <LittleFS.h>

#include "config.h"

namespace {

uint8_t ioBuffer[HTTP_IO_BUFFER_BYTES];

bool deadlineExpired(uint32_t deadline) {
  return (int32_t)(millis() - deadline) >= 0;
}

size_t smallerOf(size_t a, size_t b) {
  return a < b ? a : b;
}

}  // namespace

String HttpService::buildAuthority() {
  String authority = BACKEND_HOST;
  if (BACKEND_PORT != 80) {
    authority += ":";
    authority += BACKEND_PORT;
  }
  return authority;
}

String HttpService::encodeQueryValue(const String& value) {
  String encoded;
  encoded.reserve(value.length() + 16);
  for (size_t i = 0; i < value.length(); ++i) {
    const char c = value[i];
    if (c == ':') {
      encoded += "%3A";
    } else if (c == ' ') {
      encoded += "%20";
    } else {
      encoded += c;
    }
  }
  return encoded;
}

bool HttpService::openConnection(WiFiClient& client) {
  if (!client.connect(BACKEND_HOST, BACKEND_PORT, HTTP_CONNECT_TIMEOUT_MS)) {
    Serial.printf("Error: no fue posible conectar con %s\n", buildAuthority().c_str());
    return false;
  }
  return true;
}

bool HttpService::writeAll(WiFiClient& client, const uint8_t* data, size_t length) {
  size_t sent = 0;
  uint32_t deadline = millis() + HTTP_READ_TIMEOUT_MS;

  while (sent < length) {
    const size_t written = client.write(data + sent, length - sent);
    if (written > 0) {
      sent += written;
      deadline = millis() + HTTP_READ_TIMEOUT_MS;
      continue;
    }
    if (!client.connected() || deadlineExpired(deadline)) {
      return false;
    }
    delay(5);
  }
  return true;
}

bool HttpService::writeText(WiFiClient& client, const String& text) {
  return writeAll(client, reinterpret_cast<const uint8_t*>(text.c_str()), text.length());
}

bool HttpService::readLine(WiFiClient& client, String& line, uint32_t deadline) {
  line = "";
  while (true) {
    if (client.available() > 0) {
      const int c = client.read();
      if (c == '\n') {
        if (line.endsWith("\r")) {
          line.remove(line.length() - 1);
        }
        return true;
      }
      line += static_cast<char>(c);
      if (line.length() > 1024) {
        return false;
      }
      continue;
    }
    if (!client.connected()) {
      return line.length() > 0;
    }
    if (deadlineExpired(deadline)) {
      return false;
    }
    delay(2);
  }
}

bool HttpService::readResponseHead(WiFiClient& client, uint32_t deadline, ResponseHead& head) {
  if (!readLine(client, head.statusLine, deadline) || head.statusLine.isEmpty()) {
    Serial.println("Error: el servidor no devolvió una respuesta HTTP.");
    return false;
  }

  const int firstSpace = head.statusLine.indexOf(' ');
  if (firstSpace < 0) {
    Serial.printf("Error: línea HTTP inválida: %s\n", head.statusLine.c_str());
    return false;
  }
  head.statusCode = head.statusLine.substring(firstSpace + 1).toInt();

  String line;
  while (readLine(client, line, deadline)) {
    if (line.isEmpty()) {
      return true;
    }
    const int colon = line.indexOf(':');
    if (colon < 0) {
      continue;
    }
    String name = line.substring(0, colon);
    String value = line.substring(colon + 1);
    name.trim();
    name.toLowerCase();
    value.trim();

    if (name == "content-length") {
      head.contentLength = value.toInt();
    } else if (name == "transfer-encoding") {
      value.toLowerCase();
      head.chunked = value.indexOf("chunked") >= 0;
    }
  }

  Serial.println("Error: encabezados HTTP incompletos.");
  return false;
}

bool HttpService::readExact(WiFiClient& client, size_t count, String& output, uint32_t deadline) {
  size_t received = 0;
  while (received < count) {
    if (client.available() > 0) {
      output += static_cast<char>(client.read());
      ++received;
      continue;
    }
    if (!client.connected() || deadlineExpired(deadline)) {
      return false;
    }
    delay(2);
  }
  return true;
}

bool HttpService::readSmallBody(WiFiClient& client, const ResponseHead& head, String& body,
                                uint32_t deadline) {
  body = "";

  if (head.chunked) {
    String sizeLine;
    while (true) {
      if (!readLine(client, sizeLine, deadline)) {
        return false;
      }
      const int semicolon = sizeLine.indexOf(';');
      if (semicolon >= 0) {
        sizeLine = sizeLine.substring(0, semicolon);
      }
      sizeLine.trim();
      const long chunkSize = strtol(sizeLine.c_str(), nullptr, 16);

      if (chunkSize <= 0) {
        String trailer;
        while (readLine(client, trailer, deadline) && !trailer.isEmpty()) {
        }
        return true;
      }
      if (body.length() + chunkSize > HTTP_STT_RESPONSE_MAX_BYTES) {
        Serial.println("Error: la respuesta HTTP supera el límite permitido.");
        return false;
      }
      if (!readExact(client, chunkSize, body, deadline)) {
        return false;
      }
      String chunkEnd;
      readLine(client, chunkEnd, deadline);
    }
  }

  if (head.contentLength >= 0) {
    if ((size_t)head.contentLength > HTTP_STT_RESPONSE_MAX_BYTES) {
      Serial.println("Error: la respuesta HTTP supera el límite permitido.");
      return false;
    }
    body.reserve(head.contentLength);
    return readExact(client, head.contentLength, body, deadline);
  }

  // No length information: read until the server closes the connection.
  while (true) {
    if (client.available() > 0) {
      body += static_cast<char>(client.read());
      if (body.length() > HTTP_STT_RESPONSE_MAX_BYTES) {
        Serial.println("Error: la respuesta HTTP supera el límite permitido.");
        return false;
      }
      continue;
    }
    if (!client.connected()) {
      return true;
    }
    if (deadlineExpired(deadline)) {
      return false;
    }
    delay(2);
  }
}

bool HttpService::downloadAudio(const String& audioFile, const char* destinationPath) {
  if (audioFile.isEmpty()) {
    Serial.println("Error: el recordatorio no contiene audio_file.");
    return false;
  }

  const String path = String(AUDIO_ENDPOINT_PREFIX) + audioFile + "/";
  const String tempPath = String(destinationPath) + ".tmp";

  Serial.printf("Descargando audio desde: http://%s%s\n", buildAuthority().c_str(), path.c_str());

  WiFiClient client;
  if (!openConnection(client)) {
    return false;
  }

  // HTTP/1.0 keeps the server from answering with chunked encoding.
  const String request = "GET " + path + " HTTP/1.0\r\n" +
                         "Host: " + buildAuthority() + "\r\n" +
                         "Connection: close\r\n\r\n";

  if (!writeText(client, request)) {
    Serial.println("Error: no fue posible enviar la petición de audio.");
    client.stop();
    return false;
  }

  ResponseHead head;
  if (!readResponseHead(client, millis() + HTTP_READ_TIMEOUT_MS, head)) {
    client.stop();
    return false;
  }

  Serial.printf("Respuesta audio: HTTP %d\n", head.statusCode);
  if (head.statusCode != 200) {
    client.stop();
    return false;
  }
  if (head.chunked) {
    Serial.println("Error: respuesta chunked no soportada para la descarga de audio.");
    client.stop();
    return false;
  }

  LittleFS.remove(tempPath);
  File output = LittleFS.open(tempPath, "w");
  if (!output) {
    Serial.println("Error: no fue posible crear el archivo temporal de audio.");
    client.stop();
    return false;
  }

  size_t bytesWritten = 0;
  uint32_t lastData = millis();
  bool failed = false;

  while (head.contentLength < 0 || bytesWritten < (size_t)head.contentLength) {
    const int available = client.available();
    if (available > 0) {
      size_t toRead = smallerOf((size_t)available, sizeof(ioBuffer));
      if (head.contentLength >= 0) {
        toRead = smallerOf(toRead, (size_t)head.contentLength - bytesWritten);
      }
      const int readCount = client.read(ioBuffer, toRead);
      if (readCount <= 0) {
        continue;
      }
      if (output.write(ioBuffer, readCount) != (size_t)readCount) {
        Serial.println("Error: no fue posible escribir el audio en LittleFS.");
        failed = true;
        break;
      }
      bytesWritten += readCount;
      lastData = millis();
      continue;
    }
    if (!client.connected()) {
      break;
    }
    if (millis() - lastData > HTTP_READ_TIMEOUT_MS) {
      Serial.println("Error: la descarga dejó de recibir datos.");
      failed = true;
      break;
    }
    delay(2);
  }

  output.close();
  client.stop();

  if (!failed && head.contentLength >= 0 && bytesWritten != (size_t)head.contentLength) {
    Serial.printf("Error: descarga incompleta (%u de %ld bytes).\n", (unsigned)bytesWritten,
                  head.contentLength);
    failed = true;
  }
  if (!failed && bytesWritten == 0) {
    Serial.println("Error: el archivo de audio descargado está vacío.");
    failed = true;
  }

  if (failed) {
    LittleFS.remove(tempPath);
    return false;
  }

  LittleFS.remove(destinationPath);
  if (!LittleFS.rename(tempPath, destinationPath)) {
    Serial.println("Error: no fue posible renombrar el archivo de audio.");
    LittleFS.remove(tempPath);
    return false;
  }

  Serial.printf("WAV descargado correctamente: %u bytes\n", (unsigned)bytesWritten);
  return true;
}

bool HttpService::submitResponseFile(const String& macAddress, long assignmentId,
                                     uint32_t sampleRate, const char* pcmPath, SttResult& result) {
  if (macAddress.isEmpty() || assignmentId <= 0) {
    Serial.println("Error: mac_address y assignment_id son obligatorios.");
    return false;
  }

  File pcmFile = LittleFS.open(pcmPath, "r");
  if (!pcmFile) {
    Serial.println("Error: no existe el archivo PCM de respuesta.");
    return false;
  }

  const size_t contentLength = pcmFile.size();
  if (contentLength == 0) {
    Serial.println("Error: el archivo PCM de respuesta está vacío.");
    pcmFile.close();
    return false;
  }

  const String path = String(STT_ENDPOINT) + "?assignment_id=" + String(assignmentId) +
                      "&mac_address=" + encodeQueryValue(macAddress) +
                      "&sample_rate=" + String((unsigned long)sampleRate);

  Serial.printf("Enviando respuesta de voz a: http://%s%s\n", buildAuthority().c_str(),
                path.c_str());

  WiFiClient client;
  if (!openConnection(client)) {
    pcmFile.close();
    return false;
  }

  const String request = "POST " + path + " HTTP/1.1\r\n" +
                         "Host: " + buildAuthority() + "\r\n" +
                         "Content-Type: application/octet-stream\r\n" +
                         "Content-Length: " + String((unsigned long)contentLength) + "\r\n" +
                         "Connection: close\r\n\r\n";

  bool ok = writeText(client, request);
  size_t uploadedBytes = 0;

  while (ok) {
    const size_t count = pcmFile.read(ioBuffer, sizeof(ioBuffer));
    if (count == 0) {
      break;
    }
    ok = writeAll(client, ioBuffer, count);
    uploadedBytes += count;
  }
  pcmFile.close();

  if (!ok || uploadedBytes != contentLength) {
    Serial.printf("Error: audio enviado incompleto (%u de %u bytes).\n", (unsigned)uploadedBytes,
                  (unsigned)contentLength);
    client.stop();
    return false;
  }

  Serial.printf("Audio enviado: %u bytes\n", (unsigned)uploadedBytes);
  Serial.printf("Esperando respuesta STT (máximo %lu segundos)...\n",
                (unsigned long)(HTTP_STT_TIMEOUT_MS / 1000));

  const uint32_t deadline = millis() + HTTP_STT_TIMEOUT_MS;
  ResponseHead head;
  String body;

  if (!readResponseHead(client, deadline, head) || !readSmallBody(client, head, body, deadline)) {
    Serial.println("Error: no se recibió una respuesta STT completa.");
    client.stop();
    return false;
  }
  client.stop();

  Serial.printf("Respuesta STT: %s\n", head.statusLine.c_str());

  if (head.statusCode < 200 || head.statusCode >= 300) {
    Serial.printf("Error HTTP %d en STT: %s\n", head.statusCode, body.c_str());
    return false;
  }

  JsonDocument doc;
  const DeserializationError error = deserializeJson(doc, body);
  if (error) {
    Serial.printf("Error al procesar JSON de STT: %s\n", error.c_str());
    return false;
  }

  Serial.print("Respuesta de procesamiento: ");
  serializeJson(doc, Serial);
  Serial.println();

  result.assignmentId = doc["assignment_id"] | 0L;
  result.transcription = doc["transcription"] | "";
  result.result = doc["result"] | "";
  result.assignmentStatus = doc["assignment_status"] | "";
  result.assignmentUpdated = doc["assignment_updated"] | false;
  return true;
}
