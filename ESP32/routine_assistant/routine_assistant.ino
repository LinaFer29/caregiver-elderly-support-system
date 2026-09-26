// ESP32 voice assistant for elderly routine reminders (Arduino/C++ port of the
// MicroPython firmware). Flow: MQTT activity -> HTTP WAV download -> Bluetooth
// A2DP playback -> touch trigger -> I2S capture -> HTTP STT submission.

#include <LittleFS.h>

#include "ActivityService.h"
#include "BluetoothPlayer.h"
#include "HttpService.h"
#include "Microphone.h"
#include "MqttService.h"
#include "TouchSensor.h"
#include "WifiService.h"
#include "config.h"

WifiService wifiService;
MqttService mqttService(wifiService);
HttpService httpService;
BluetoothPlayer bluetoothPlayer;
Microphone microphone;
TouchSensor touchSensor;
ActivityService activityService(httpService, bluetoothPlayer, microphone, touchSensor);

String macAddress;

void haltWithError(const char* message) {
  Serial.println(message);
  while (true) {
    delay(1000);
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("================================");
  Serial.println(" ASISTENTE DE RUTINAS - ESP32");
  Serial.println("================================");

  if (!LittleFS.begin(true)) {
    haltWithError("Error: no fue posible montar LittleFS.");
  }

  touchSensor.begin();

  if (!microphone.begin()) {
    haltWithError("Error: no fue posible inicializar el micrófono.");
  }

  if (!bluetoothPlayer.begin()) {
    haltWithError("Error: no fue posible inicializar Bluetooth.");
  }

  wifiService.ensureConnected();
  macAddress = wifiService.getMacAddress();
  Serial.printf("MAC del dispositivo: %s\n", macAddress.c_str());

  Serial.println("Esperando conexión con el parlante Bluetooth...");
  if (bluetoothPlayer.waitForConnection(BT_CONNECT_WAIT_MS)) {
    Serial.println("Parlante Bluetooth conectado.");
  } else {
    Serial.println("Parlante aún no conectado; se seguirá intentando en segundo plano.");
  }

  Serial.printf("Heap libre: %lu bytes\n", (unsigned long)ESP.getFreeHeap());
}

void loop() {
  Activity activity;
  if (!mqttService.waitForActivity(macAddress, activity)) {
    return;
  }

  // Same policy as the MicroPython firmware: MQTT is closed while the activity
  // runs (the STT call can block up to two minutes) and reopened afterwards.
  Serial.println("Actividad MQTT recibida. Cerrando MQTT durante el procesamiento.");
  mqttService.disconnect();

  activityService.process(activity, macAddress);

  Serial.println();
  Serial.printf("Heap libre: %lu bytes\n", (unsigned long)ESP.getFreeHeap());
}
