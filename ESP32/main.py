"""ESP32 application entry point."""

import gc
import sys
import time

from config import AUDIO_TEST_WAV_PATH, DEBUG_MEMORY, ENABLE_AUDIO_TEST
from services.wifi_service import WiFiService

_audio_dac = None


def log_memory(label, force=False):
    """Print heap diagnostics without requiring micropython on desktop checks."""

    gc.collect()
    if not force and not DEBUG_MEMORY:
        return

    print("{}: {}".format(label, gc.mem_free()))


def get_audio_dac():
    """Return the single DAC instance kept alive by the main program."""

    global _audio_dac

    if _audio_dac is None:
        from machine import DAC, Pin
        from config import PIN_AUDIO

        _audio_dac = DAC(Pin(PIN_AUDIO))
        _audio_dac.write(128)

    return _audio_dac


def run_audio_test():
    """Run the isolated WAV playback test."""

    from services.audio_service import AudioService

    print("Ejecutando prueba manual de audio WAV...")
    AudioService(dac=get_audio_dac()).play_wav(AUDIO_TEST_WAV_PATH)
    print("Prueba de audio finalizada.")


def connect_wifi():
    """Connect WiFi and return the ESP32 MAC address."""

    wifi_service = WiFiService()
    wifi_service.connect()

    if not wifi_service.is_connected():
        print("Sistema no listo: no hay conexion WiFi.")
        return None

    mac_address = wifi_service.get_mac_address()
    print("MAC del dispositivo:", mac_address)
    print("")

    del wifi_service
    log_memory("Heap después WiFi")
    return mac_address


def unload_modules(module_names):
    """Drop selected dynamically imported modules from sys.modules."""

    for module_name in module_names:
        try:
            if module_name in sys.modules:
                del sys.modules[module_name]
        except Exception:
            pass

    gc.collect()


def wait_for_activity(mac_address):
    """Wait for one MQTT activity and release MQTT before returning it."""

    mqtt_service = None
    log_memory("Heap antes de importar MQTTService")

    from services.mqtt_service import MQTTService

    log_memory("Heap después de importar MQTTService")

    try:
        mqtt_service = MQTTService()
        return mqtt_service.wait_for_activity(mac_address)
    finally:
        if mqtt_service is not None:
            try:
                mqtt_service.close()
            except Exception as exc:
                print("No fue posible cerrar MQTTService:", exc)

            del mqtt_service

        unload_modules(("services.mqtt_service", "umqtt.simple"))
        log_memory("Heap después de liberar MQTTService")


def process_activity(mac_address, payload):
    """Process one activity after MQTT has been fully released."""

    activity_service = None
    log_memory("Heap antes de importar ActivityService")

    from services.activity_service import ActivityService

    log_memory("Heap después de importar ActivityService")

    try:
        activity_service = ActivityService(
            mac_address=mac_address,
            dac=get_audio_dac(),
        )
        return activity_service.process(payload)
    except Exception as exc:
        print("Error no controlado procesando actividad:", type(exc).__name__, repr(exc))
        return False
    finally:
        if activity_service is not None:
            try:
                activity_service.cleanup()
            except Exception as exc:
                print("Error durante cleanup de actividad:", exc)

            del activity_service

        unload_modules((
            "services.activity_service",
            "services.http_service",
            "services.audio_service",
            "services.microphone_service",
            "urequests",
        ))
        log_memory("Heap después de liberar ActivityService")


def main():
    """Start the ESP32 in audio-test or MQTT mode."""

    log_memory("Heap en boot", force=True)

    if ENABLE_AUDIO_TEST:
        run_audio_test()
        return

    mac_address = connect_wifi()
    if not mac_address:
        return

    print("Modo normal MQTT.")

    while True:
        payload = wait_for_activity(mac_address)

        if payload is not None:
            process_activity(mac_address, payload)

        print("")
        print("Actividad finalizada. Volviendo a esperar MQTT...")
        time.sleep(1)


main()
