"""ESP32 application entry point."""

from services.http_service import HttpService
from services.wifi_service import WiFiService


wifi_service = WiFiService()
wifi_service.connect()

if wifi_service.is_connected():
    http = HttpService()
    reminders = http.get_reminders(elderly_id=1)

    if reminders is None:
        print("No fue posible obtener los recordatorios del servidor.")
    elif len(reminders) == 0:
        print("No hay recordatorios pendientes.")
    else:
        for reminder in reminders:
            scheduled_time = reminder.scheduled_time or ""
            display_time = scheduled_time[:5] if len(scheduled_time) >= 5 else scheduled_time

            print("--------------------------------")
            print("Actividad:")
            print(reminder.activity)
            print("")
            print("Hora:")
            print(display_time)
            print("")
            print("Mensaje:")
            print(reminder.message)
            print("--------------------------------")

    print("Sistema listo para las siguientes integraciones.")
else:
    print("Sistema no listo: no hay conexion WiFi.")
