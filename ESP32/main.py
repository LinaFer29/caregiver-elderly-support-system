"""ESP32 application entry point."""

from services.http_service import HttpService
from services.wifi_service import WiFiService


wifi_service = WiFiService()
wifi_service.connect()

if wifi_service.is_connected():
    mac_address = wifi_service.get_mac_address()
    print("MAC del dispositivo:", mac_address)
    print("")
    print("Consultando recordatorios...")

    http = HttpService()
    reminders = http.get_reminders(mac_address=mac_address)

    if reminders is None:
        print("No fue posible obtener los recordatorios del servidor.")
    elif len(reminders) == 0:
        print("No hay recordatorios pendientes.")
    else:
        print("")
        print("Se recibieron {} recordatorios.".format(len(reminders)))
        print("")
        for reminder in reminders:
            print("• {}".format(reminder.message))

    print("Sistema listo para las siguientes integraciones.")
else:
    print("Sistema no listo: no hay conexion WiFi.")
