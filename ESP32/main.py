"""ESP32 application entry point."""

from services.http_service import HttpService
from services.wifi_service import WiFiService


wifi_service = WiFiService()
wifi_service.connect()

if wifi_service.is_connected():
    http_service = HttpService()
    response_data = http_service.get("/api/voice/reminders?elderly_id=7")
    print("Respuesta del backend:", response_data)
    print("Sistema listo para las siguientes integraciones.")
else:
    print("Sistema no listo: no hay conexion WiFi.")
