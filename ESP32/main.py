"""ESP32 application entry point."""

from config import AUDIO_TEST_WAV_PATH, ENABLE_AUDIO_TEST
from services.audio_service import AudioService
from services.mqtt_service import MQTTService
from services.wifi_service import WiFiService

if ENABLE_AUDIO_TEST:
    print("Ejecutando prueba manual de audio WAV...")
    AudioService().play_wav(AUDIO_TEST_WAV_PATH)
    print("Prueba de audio finalizada.")
else:
    wifi_service = WiFiService()
    wifi_service.connect()

    if wifi_service.is_connected():
        mac_address = wifi_service.get_mac_address()
        print("MAC del dispositivo:", mac_address)
        print("")
        mqtt_service = MQTTService()
        mqtt_service.listen_forever(mac_address)
    else:
        print("Sistema no listo: no hay conexion WiFi.")
