"""ESP32 application entry point."""

from config import AUDIO_TEST_WAV_PATH, ENABLE_AUDIO_TEST
from services.audio_service import AudioService
from services.http_service import HttpService
from services.wifi_service import WiFiService

if ENABLE_AUDIO_TEST:
    print("Ejecutando prueba manual de audio WAV...")
    AudioService().play_wav(AUDIO_TEST_WAV_PATH)
    print("Prueba de audio finalizada.")
else:
    wifi_service = WiFiService()
    wifi_service.connect()

    if wifi_service.is_connected():
        audio_service = AudioService()
        http_service = HttpService()
        mac_address = wifi_service.get_mac_address()
        print("MAC del dispositivo:", mac_address)
        print("")
        print("Consultando recordatorios...")

        reminders = http_service.get_reminders(mac_address=mac_address)

        if reminders is None:
            print("No fue posible obtener los recordatorios del servidor.")
        elif len(reminders) == 0:
            print("No hay recordatorios pendientes.")
        else:
            print("Recordatorios recibidos:", len(reminders))
            reminder = reminders[0]
            scheduled_time = reminder.scheduled_time or ""
            display_time = (
                scheduled_time[:5]
                if len(scheduled_time) >= 5
                else scheduled_time
            )

            print("--------------------------------")
            print("Recordatorio seleccionado:")
            print("Actividad:", reminder.activity)
            print("Hora:", display_time)
            print("Mensaje:", reminder.message)
            print("Audio:", reminder.audio_file)
            print("--------------------------------")

            if not reminder.audio_file:
                print("El recordatorio recibido no incluye audio_file.")
            else:
                print("Descargando audio...")
                audio_path = http_service.download_audio(reminder.audio_file)

                if audio_path is None:
                    print("No fue posible descargar el audio del recordatorio.")
                else:
                    print("Reproduciendo recordatorio...")
                    try:
                        audio_service.play_wav(audio_path)
                        print("Reproducción terminada.")
                    except Exception as exc:
                        print("Error durante la reproducción del WAV:", exc)
    else:
        print("Sistema no listo: no hay conexion WiFi.")
