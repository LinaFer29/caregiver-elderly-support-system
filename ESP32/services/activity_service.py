"""Activity processing flow for the ESP32 voice assistant."""

import gc
import os
import sys

from config import DEBUG_MEMORY

RESPONSE_PCM_PATH = "/assistant_response.pcm"


def log_memory(label, force=False):
    """Print heap diagnostics, including fragmentation details when available."""

    gc.collect()
    if force or DEBUG_MEMORY:
        print("{}: {}".format(label, gc.mem_free()))


def unload_module(module_name):
    """Release a non-builtin module if it was imported for the current phase."""

    try:
        if module_name in sys.modules:
            del sys.modules[module_name]
    except Exception:
        pass

    gc.collect()


class ActivityService:
    """Run one MQTT activity through HTTPS download, audio, microphone and STT."""

    def __init__(self, mac_address, dac):
        self._mac_address = mac_address
        self._dac = dac

    def process(self, payload_json):
        """Process one activity payload using the lowest-memory phase ordering."""

        activity = self._extract_activity(payload_json)

        if activity is None:
            return False

        self._print_activity(activity)

        wav_path = self._download_audio(activity["audio_file"])

        if not wav_path:
            print("No fue posible descargar el audio del recordatorio.")
            return False

        if not self._play_audio(wav_path):
            return False

        response_result = self._capture_and_submit_response(activity["assignment_id"])

        if response_result is None:
            print("No fue posible procesar la respuesta hablada.")
            return False

        self._print_response_result(response_result)
        return True

    def cleanup(self):
        """Force a final collection after an activity flow."""

        print("")
        print("Liberando recursos de actividad...")
        log_memory("Heap después de liberar recursos")

    def _extract_activity(self, payload_json):
        """Extract only the fields needed before importing heavier modules."""

        if not isinstance(payload_json, dict):
            print("Error: el payload de actividad no es un diccionario JSON.")
            return None

        assignment_id = payload_json.get("assignment_id")
        audio_file = payload_json.get("audio_file")

        if not audio_file:
            print("Error: el mensaje no contiene audio_file.")
            return None

        if not assignment_id:
            print("Error: el mensaje no contiene assignment_id.")
            return None

        return {
            "assignment_id": assignment_id,
            "audio_file": audio_file,
            "activity": payload_json.get("activity") or payload_json.get("title"),
            "message": payload_json.get("message") or payload_json.get("description"),
        }

    def _print_activity(self, activity):
        print("")
        print("Actividad recibida:")
        print("ID assignment:", activity["assignment_id"])
        print("Actividad:", activity["activity"])
        print("Mensaje:", activity["message"])
        print("Audio:", activity["audio_file"])

    def _download_audio(self, audio_file):
        """Download the WAV before loading DAC/I2S/microphone modules."""

        log_memory("Heap antes de importar HttpService")

        from services.http_service import HttpService

        log_memory("Heap después de importar HttpService")
        http_service = HttpService()

        try:
            print("")
            print("Descargando audio del recordatorio...")
            log_memory("Heap antes de HTTPS audio", force=True)
            wav_path = http_service.download_audio(audio_file)
            log_memory("Heap después de HTTPS audio")
            return wav_path
        finally:
            del http_service
            unload_module("urequests")
            gc.collect()

    def _play_audio(self, wav_path):
        """Load audio output only after the WAV has been downloaded."""

        log_memory("Heap antes AudioService")

        from services.audio_service import AudioService

        log_memory("Heap después AudioService")
        audio_service = AudioService(dac=self._dac)

        try:
            print("Reproduciendo recordatorio...")
            audio_service.play_wav(wav_path)
            print("Reproducción terminada.")
            return True
        except Exception as exc:
            print("Error durante la reproducción del audio:", exc)
            return False
        finally:
            try:
                audio_service.release_output()
            except Exception as exc:
                print("No fue posible liberar el DAC:", exc)

            del audio_service
            gc.collect()

    def _capture_and_submit_response(self, assignment_id):
        """Capture PCM to flash, then submit it after I2S has been released."""

        log_memory("Heap antes MicrophoneService")

        from services.microphone_service import MicrophoneService

        log_memory("Heap después MicrophoneService")
        microphone_service = MicrophoneService()
        sample_rate = microphone_service.sample_rate
        capture_success = False

        try:
            try:
                os.remove(RESPONSE_PCM_PATH)
            except OSError:
                pass

            capture_info = microphone_service.record_pcm16_to_file(RESPONSE_PCM_PATH)
            capture_success = True
        except Exception as exc:
            print("Error al capturar respuesta de voz:", exc)
            return None
        finally:
            try:
                microphone_service.release()
            except Exception as exc:
                print("No fue posible liberar I2S RX:", exc)

            if not capture_success:
                try:
                    os.remove(RESPONSE_PCM_PATH)
                except OSError:
                    pass

            del microphone_service
            unload_module("services.microphone_service")
            gc.collect()
            log_memory("Heap después captura y liberar I2S", force=True)

        log_memory("Heap antes importar HttpService STT")

        from services.http_service import HttpService

        log_memory("Heap después importar HttpService STT")
        http_service = HttpService()

        try:
            log_memory("Heap antes HTTPS STT", force=True)
            response_result = http_service.submit_assignment_response_file(
                mac_address=self._mac_address,
                assignment_id=assignment_id,
                sample_rate=sample_rate,
                pcm_path=RESPONSE_PCM_PATH,
            )
            log_memory("Heap después STT", force=True)

            if response_result and capture_info:
                response_result["capture_info"] = capture_info

            return response_result
        finally:
            try:
                os.remove(RESPONSE_PCM_PATH)
            except OSError:
                pass

            del http_service
            unload_module("urequests")
            gc.collect()

    def _print_response_result(self, response_result):
        print("")
        print("Resultado de la respuesta:")
        print("Assignment:", response_result.get("assignment_id"))
        print("Transcripción:", response_result.get("transcription"))
        print("Resultado:", response_result.get("result"))
        print("Estado final:", response_result.get("assignment_status"))
        print("Actualizada:", response_result.get("assignment_updated"))
