"""HTTP communication service for the ESP32 MicroPython application."""

import json
import os
import socket
from time import sleep_ms

import urequests

from config import (
    AUDIO_ENDPOINT_PREFIX,
    BACKEND_HOST,
    BACKEND_PORT,
    HTTP_AUDIO_MAX_CONSECUTIVE_TIMEOUTS,
    HTTP_AUDIO_READ_TIMEOUT_SECONDS,
    HTTP_CONNECT_TIMEOUT_SECONDS,
    HTTP_SEND_TIMEOUT_SECONDS,
    HTTP_STT_RESPONSE_MAX_BYTES,
    HTTP_STT_TIMEOUT_SECONDS,
    REMINDERS_ENDPOINT,
    STT_ENDPOINT,
    TEMP_AUDIO_DOWNLOAD_PATH,
)
from models.reminder import Reminder


class HttpService:
    """Encapsulate HTTP requests to the backend API.

    This service is responsible only for building backend URLs, executing HTTP
    requests, and safely handling transport or response errors.
    """

    def __init__(self, host=BACKEND_HOST, port=BACKEND_PORT):
        """Initialize the service with backend connection settings."""

        self._host = host
        self._port = port

    def _build_url(self, endpoint):
        """Build a full backend URL from a relative endpoint."""

        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint

        return "http://{}:{}{}".format(self._host, self._port, endpoint)

    def _encode_query_value(self, value):
        text = str(value or "")
        return text.replace(":", "%3A").replace(" ", "%20")

    def _set_socket_timeout(self, client, seconds):
        try:
            client.settimeout(seconds)
        except AttributeError:
            pass

    def _open_http_socket(self):
        """Open a plain HTTP socket to the configured backend."""

        address = socket.getaddrinfo(
            self._host,
            self._port,
            0,
            socket.SOCK_STREAM,
        )[0][-1]

        client = socket.socket()
        self._set_socket_timeout(client, HTTP_CONNECT_TIMEOUT_SECONDS)
        client.connect(address)
        self._set_socket_timeout(client, HTTP_SEND_TIMEOUT_SECONDS)
        return client

    def _write_all(self, client, data):
        """Write the full byte sequence to the socket."""

        view = memoryview(data)
        sent = 0

        while sent < len(view):
            written = client.write(view[sent:])

            if written is None:
                return

            if written <= 0:
                raise OSError("El socket dejó de aceptar datos.")

            sent += written

    def _read_exact(self, client, size):
        """Read an exact number of bytes from the socket."""

        data = bytearray(size)
        view = memoryview(data)
        received = 0

        while received < size:
            block = client.recv(size - received)

            if not block:
                raise OSError("La conexión terminó antes de tiempo.")

            view[received:received + len(block)] = block
            received += len(block)

        return data

    def _read_status_and_headers(self, client):
        """Read the HTTP status line and headers from a socket response."""

        status_line = client.readline()

        if not status_line:
            raise OSError("El servidor no devolvió una respuesta HTTP.")

        status_line = status_line.decode("utf-8", "replace").strip()
        parts = status_line.split()

        if len(parts) < 2:
            raise ValueError("Línea HTTP inválida: " + status_line)

        status_code = int(parts[1])
        headers = {}

        while True:
            line = client.readline()

            if not line or line in (b"\r\n", b"\n"):
                break

            text = line.decode("utf-8", "replace").strip()

            if ":" in text:
                name, value = text.split(":", 1)
                headers[name.strip().lower()] = value.strip()

        return status_line, status_code, headers

    def _read_small_body(self, client, headers, limit=4096):
        """Read a small HTTP body, useful for error details."""

        result = bytearray()
        transfer_encoding = headers.get("transfer-encoding", "").lower()

        if "chunked" in transfer_encoding:
            while True:
                size_line = client.readline()

                if not size_line:
                    raise OSError("Respuesta chunked incompleta.")

                hex_part = size_line.strip().split(b";", 1)[0]
                chunk_size = int(hex_part, 16)

                if chunk_size == 0:
                    while True:
                        trailer = client.readline()
                        if not trailer or trailer in (b"\r\n", b"\n"):
                            break
                    break

                block = self._read_exact(client, chunk_size)

                if len(result) + len(block) > limit:
                    raise MemoryError("La respuesta HTTP supera el límite permitido.")

                result.extend(block)
                self._read_exact(client, 2)

            return bytes(result)

        if "content-length" in headers:
            size = int(headers["content-length"])

            if size > limit:
                raise MemoryError("La respuesta HTTP supera el límite permitido.")

            return bytes(self._read_exact(client, size))

        while len(result) < limit:
            block = client.recv(min(512, limit - len(result)))

            if not block:
                break

            result.extend(block)

        return bytes(result)

    def _save_body_to_file(self, client, headers, destination_path):
        """Stream an HTTP response body directly to flash."""

        transfer_encoding = headers.get("transfer-encoding", "").lower()
        content_length = headers.get("content-length")
        total = 0
        consecutive_timeouts = 0

        def receive_with_retries(size):
            nonlocal consecutive_timeouts

            while True:
                try:
                    block = client.recv(size)
                    consecutive_timeouts = 0
                    return block
                except OSError as error:
                    code = error.args[0] if error.args else None

                    if code in (104, 54):
                        return None

                    if code == 116:
                        consecutive_timeouts += 1
                        print(
                            "Pausa de red durante la descarga:",
                            consecutive_timeouts,
                            "de",
                            HTTP_AUDIO_MAX_CONSECUTIVE_TIMEOUTS,
                        )

                        if consecutive_timeouts >= HTTP_AUDIO_MAX_CONSECUTIVE_TIMEOUTS:
                            raise RuntimeError(
                                "La descarga no recibió datos durante "
                                "aproximadamente {} segundos. "
                                "Se habían recibido {} bytes.".format(
                                    HTTP_AUDIO_READ_TIMEOUT_SECONDS
                                    * HTTP_AUDIO_MAX_CONSECUTIVE_TIMEOUTS,
                                    total,
                                )
                            )

                        sleep_ms(100)
                        continue

                    raise

        with open(destination_path, "wb") as output_file:
            if "chunked" in transfer_encoding:
                while True:
                    size_line = client.readline()

                    if not size_line:
                        raise OSError("Descarga chunked incompleta.")

                    hex_part = size_line.strip().split(b";", 1)[0]
                    remaining_chunk = int(hex_part, 16)

                    if remaining_chunk == 0:
                        while True:
                            trailer = client.readline()
                            if not trailer or trailer in (b"\r\n", b"\n"):
                                break
                        break

                    while remaining_chunk > 0:
                        block = receive_with_retries(min(1024, remaining_chunk))

                        if block is None:
                            raise OSError(
                                "Conexión reiniciada dentro de un chunk. "
                                "Faltaban {} bytes.".format(remaining_chunk)
                            )

                        if not block:
                            raise OSError(
                                "El WAV terminó antes de completar un chunk."
                            )

                        output_file.write(block)
                        total += len(block)
                        remaining_chunk -= len(block)

                    self._read_exact(client, 2)

                return total

            if content_length is not None:
                expected = int(content_length)
                remaining = expected

                while remaining > 0:
                    block = receive_with_retries(min(1024, remaining))

                    if block is None:
                        raise OSError(
                            "La conexión se reinició antes de completar el WAV. "
                            "Recibidos {} de {} bytes.".format(total, expected)
                        )

                    if not block:
                        raise OSError(
                            "El servidor cerró antes de completar el WAV. "
                            "Recibidos {} de {} bytes.".format(total, expected)
                        )

                    output_file.write(block)
                    total += len(block)
                    remaining -= len(block)

                return total

            while True:
                block = receive_with_retries(1024)

                if block is None:
                    if total == 0:
                        raise OSError("La conexión se reinició sin recibir el WAV.")
                    break

                if not block:
                    break

                output_file.write(block)
                total += len(block)

        return total

    def get(self, endpoint):
        """Perform a GET request and return parsed JSON or None on failure."""

        url = self._build_url(endpoint)
        response = None

        try:
            print("Realizando GET a:", url)
            response = urequests.get(url)
        except Exception as exc:
            print("Error de conexion HTTP:", exc)
            return None

        try:
            if response.status_code != 200:
                print("Error HTTP {} al consultar {}".format(response.status_code, url))
                return None

            try:
                print("HTTP", response.status_code)
                return response.json()
            except Exception as exc:
                print("Error al procesar JSON de la respuesta:", exc)
                return None
        finally:
            try:
                response.close()
            except Exception:
                pass

    def get_reminders(self, mac_address):
        """Return a list of Reminder objects for the given device MAC."""

        endpoint = "{}?mac_address={}".format(REMINDERS_ENDPOINT, mac_address)
        data = self.get(endpoint)

        if data is None:
            return None

        if not isinstance(data, list):
            print("Error: la respuesta del servidor no es una lista valida.")
            return None

        reminders = []

        try:
            for item in data:
                reminders.append(Reminder.from_dict(item))
        except Exception as exc:
            print("Error al convertir la respuesta en recordatorios:", exc)
            return None

        return reminders

    def submit_assignment_response_stream(
        self,
        mac_address,
        assignment_id,
        microphone_service,
    ):
        """Capture and submit a spoken response as PCM16 to `/assistant/stt/`."""

        if not mac_address:
            print("Error: mac_address es obligatorio para enviar la respuesta.")
            return None

        if not assignment_id:
            print("Error: assignment_id es obligatorio para enviar la respuesta.")
            return None

        endpoint = "{}?assignment_id={}&mac_address={}&sample_rate={}".format(
            STT_ENDPOINT,
            assignment_id,
            self._encode_query_value(mac_address),
            microphone_service.sample_rate,
        )
        client = None

        try:
            print("Enviando respuesta de voz a:", self._build_url(endpoint))
            client = self._open_http_socket()
            request = (
                "POST {} HTTP/1.1\r\n"
                "Host: {}:{}\r\n"
                "Content-Type: application/octet-stream\r\n"
                "Content-Length: {}\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).format(
                endpoint,
                self._host,
                self._port,
                microphone_service.total_pcm_bytes,
            ).encode()

            self._write_all(client, request)
            capture_info = microphone_service.stream_pcm16_to_sink(
                lambda chunk: self._write_all(client, chunk)
            )
            self._set_socket_timeout(client, HTTP_STT_TIMEOUT_SECONDS)

            print(
                "Esperando respuesta STT (máximo {} segundos)...".format(
                    HTTP_STT_TIMEOUT_SECONDS
                )
            )
            status_line, status_code, headers = self._read_status_and_headers(client)
            body = self._read_small_body(
                client,
                headers,
                limit=HTTP_STT_RESPONSE_MAX_BYTES,
            )
            print("Respuesta STT:", status_line)

            if status_code < 200 or status_code >= 300:
                print("Error HTTP {} en STT: {}".format(
                    status_code,
                    body.decode("utf-8", "replace"),
                ))
                return None

            response_json = json.loads(body.decode("utf-8"))
            print("Respuesta de procesamiento:", response_json)

            if capture_info:
                response_json["capture_info"] = capture_info

            return response_json
        except Exception as exc:
            print("Error al enviar la respuesta de voz:", exc)
            return None
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass

    def download_audio(self, audio_file, destination_path=TEMP_AUDIO_DOWNLOAD_PATH):
        """Download a WAV file to flash without loading it fully into RAM."""

        if not audio_file:
            print("Error: el recordatorio no contiene audio_file.")
            return None

        endpoint = "{}{}/".format(AUDIO_ENDPOINT_PREFIX, audio_file)
        client = None

        try:
            print("Descargando audio desde:", self._build_url(endpoint))
            client = self._open_http_socket()
            request = (
                "GET {} HTTP/1.1\r\n"
                "Host: {}:{}\r\n"
                "Accept: */*\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).format(endpoint, self._host, self._port).encode()

            self._write_all(client, request)
            self._set_socket_timeout(client, HTTP_AUDIO_READ_TIMEOUT_SECONDS)
        except Exception as exc:
            print("Error de conexion HTTP al descargar audio:", exc)
            return None

        try:
            status_line, status_code, headers = self._read_status_and_headers(client)
            print("Respuesta audio:", status_line)

            if status_code < 200 or status_code >= 300:
                error_body = self._read_small_body(client, headers)
                print(
                    "Error HTTP {} al descargar audio: {}".format(
                        status_code,
                        error_body.decode("utf-8", "replace"),
                    )
                )
                return None

            try:
                os.remove(destination_path)
            except OSError:
                pass

            bytes_written = self._save_body_to_file(
                client,
                headers,
                destination_path,
            )

            if bytes_written <= 0:
                print("Error: el archivo de audio descargado está vacío.")
                try:
                    os.remove(destination_path)
                except OSError:
                    pass
                return None

            print("WAV descargado correctamente:", bytes_written, "bytes")
            return destination_path
        except Exception as exc:
            print("Error al guardar el WAV descargado:", exc)
            try:
                os.remove(destination_path)
            except OSError:
                pass
            return None
        finally:
            try:
                if client is not None:
                    client.close()
            except Exception:
                pass
