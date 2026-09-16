"""HTTP communication service for the ESP32 MicroPython application."""

import gc
import json
import os
import socket
from time import sleep_ms

try:
    import ssl
except ImportError:
    try:
        import ussl as ssl
    except ImportError:
        ssl = None

from config import (
    AUDIO_ENDPOINT_PREFIX,
    BACKEND_HOST,
    BACKEND_SCHEME,
    BACKEND_PORT,
    HTTP_AUDIO_MAX_CONSECUTIVE_TIMEOUTS,
    HTTP_AUDIO_STREAM_BUFFER_BYTES,
    HTTP_CONNECT_TIMEOUT_SECONDS,
    HTTP_SEND_TIMEOUT_SECONDS,
    HTTP_STT_RESPONSE_MAX_BYTES,
    HTTP_STT_TIMEOUT_SECONDS,
    REMINDERS_ENDPOINT,
    STT_ENDPOINT,
    TEMP_AUDIO_DOWNLOAD_PATH,
)


class HttpService:
    """Encapsulate HTTP requests to the backend API.

    This service is responsible only for building backend URLs, executing HTTP
    requests, and safely handling transport or response errors.
    """

    def __init__(self, scheme=BACKEND_SCHEME, host=BACKEND_HOST, port=BACKEND_PORT):
        """Initialize the service with backend connection settings."""

        self._scheme = (scheme or "http").lower()
        self._host = host
        self._port = port

    def _is_https(self):
        return self._scheme == "https"

    def _is_default_port(self):
        return (self._is_https() and self._port == 443) or (
            not self._is_https() and self._port == 80
        )

    def _build_authority(self):
        if self._is_default_port():
            return self._host

        return "{}:{}".format(self._host, self._port)

    def _build_url(self, endpoint):
        """Build a full backend URL from a relative endpoint."""

        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint

        return "{}://{}{}".format(
            self._scheme,
            self._build_authority(),
            endpoint,
        )

    def _encode_query_value(self, value):
        text = str(value or "")
        return text.replace(":", "%3A").replace(" ", "%20")

    def _set_socket_timeout(self, client, seconds):
        try:
            client.settimeout(seconds)
        except AttributeError:
            pass

    def _open_http_socket(self):
        """Open an HTTP or HTTPS socket to the configured backend."""

        address = socket.getaddrinfo(
            self._host,
            self._port,
            0,
            socket.SOCK_STREAM,
        )[0][-1]

        client = socket.socket()
        self._set_socket_timeout(client, HTTP_CONNECT_TIMEOUT_SECONDS)
        client.connect(address)

        if not self._is_https():
            self._set_socket_timeout(client, HTTP_SEND_TIMEOUT_SECONDS)
            return client

        if ssl is None:
            client.close()
            raise RuntimeError(
                "El firmware actual no expone ssl/ussl. "
                "HTTPS no está disponible para el ESP32."
            )

        try:
            client = self._wrap_tls_socket(client)
        except Exception:
            try:
                client.close()
            except Exception:
                pass
            raise

        self._set_socket_timeout(client, HTTP_SEND_TIMEOUT_SECONDS)
        return client

    def _wrap_tls_socket(self, client):
        """Wrap a connected socket with TLS when HTTPS is configured."""

        wrap_socket = getattr(ssl, "wrap_socket", None)

        if wrap_socket is None:
            raise RuntimeError(
                "El módulo ssl/ussl disponible no soporta wrap_socket()."
            )

        try:
            wrapped = wrap_socket(client, server_hostname=self._host)
        except TypeError:
            wrapped = wrap_socket(client)
            print(
                "Advertencia: TLS activo sin SNI explícito; "
                "depende del firmware si el handshake funcionará."
            )

        if not hasattr(ssl, "CERT_REQUIRED"):
            print(
                "Advertencia: el firmware MicroPython actual no expone "
                "validación estándar de certificados TLS."
            )

        return wrapped

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

    def get(self, endpoint):
        """Perform a GET request and return parsed JSON or None on failure."""

        url = self._build_url(endpoint)
        response = None

        try:
            print("Realizando GET a:", url)
            import urequests

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

        from models.reminder import Reminder

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
                "Host: {}\r\n"
                "Content-Type: application/octet-stream\r\n"
                "Content-Length: {}\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).format(
                endpoint,
                self._build_authority(),
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

    def submit_assignment_response_file(
        self,
        mac_address,
        assignment_id,
        sample_rate,
        pcm_path,
    ):
        """Submit a recorded PCM16 file to `/assistant/stt/` without buffering it."""

        if not mac_address:
            print("Error: mac_address es obligatorio para enviar la respuesta.")
            return None

        if not assignment_id:
            print("Error: assignment_id es obligatorio para enviar la respuesta.")
            return None

        content_length = os.stat(pcm_path)[6]

        if content_length <= 0:
            print("Error: el archivo PCM de respuesta está vacío.")
            return None

        endpoint = "{}?assignment_id={}&mac_address={}&sample_rate={}".format(
            STT_ENDPOINT,
            assignment_id,
            self._encode_query_value(mac_address),
            sample_rate,
        )
        client = None

        try:
            print("Enviando respuesta de voz a:", self._build_url(endpoint))
            client = self._open_http_socket()
            request = (
                "POST {} HTTP/1.1\r\n"
                "Host: {}\r\n"
                "Content-Type: application/octet-stream\r\n"
                "Content-Length: {}\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).format(
                endpoint,
                self._build_authority(),
                content_length,
            ).encode()

            self._write_all(client, request)

            uploaded_bytes = 0
            upload_buffer = bytearray(1024)
            upload_view = memoryview(upload_buffer)

            with open(pcm_path, "rb") as pcm_file:
                while True:
                    count = pcm_file.readinto(upload_buffer)

                    if not count:
                        break

                    self._write_all(client, upload_view[:count])
                    uploaded_bytes += count

            if uploaded_bytes != content_length:
                raise OSError(
                    "Audio enviado incompleto: esperados {} bytes, enviados {}.".format(
                        content_length,
                        uploaded_bytes,
                    )
                )

            print("Audio enviado:", uploaded_bytes, "bytes")
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
        """Download a WAV file with urequests streaming directly to flash."""

        if not audio_file:
            print("Error: el recordatorio no contiene audio_file.")
            return None

        endpoint = "{}{}/".format(AUDIO_ENDPOINT_PREFIX, audio_file)
        url = self._build_url(endpoint)
        temp_path = destination_path + ".tmp"
        response = None
        output_file = None
        bytes_written = 0
        consecutive_empty_reads = 0
        next_progress_report = 32768

        try:
            gc.collect()
            print("Descargando audio desde:", url)
            print("Heap antes HTTPS audio:", gc.mem_free())

            import urequests

            response = urequests.get(url)
            status_code = response.status_code
            print("Respuesta audio: HTTP", status_code)
            gc.collect()
            print("Heap después handshake/headers:", gc.mem_free())

            if status_code != 200:
                print("Error HTTP {} al descargar audio.".format(status_code))
                return None

            try:
                os.remove(temp_path)
            except OSError:
                pass

            raw = getattr(response, "raw", None)
            if raw is None or not hasattr(raw, "readinto"):
                print("Error: la respuesta HTTP no permite streaming con raw.readinto.")
                return None

            buffer = bytearray(HTTP_AUDIO_STREAM_BUFFER_BYTES)
            view = memoryview(buffer)
            output_file = open(temp_path, "wb")

            while True:
                read_count = raw.readinto(view)

                if read_count is None:
                    consecutive_empty_reads += 1

                    if consecutive_empty_reads >= HTTP_AUDIO_MAX_CONSECUTIVE_TIMEOUTS:
                        print(
                            "Error: la descarga no entregó datos tras",
                            consecutive_empty_reads,
                            "intentos.",
                        )
                        return None

                    sleep_ms(100)
                    continue

                consecutive_empty_reads = 0

                if read_count == 0:
                    break

                output_file.write(view[:read_count])
                bytes_written += read_count

                if bytes_written >= next_progress_report:
                    print("Descargados:", bytes_written, "bytes | Heap:", gc.mem_free())
                    next_progress_report += 32768

            output_file.close()
            output_file = None

            if bytes_written <= 0:
                print("Error: el archivo de audio descargado está vacío.")
                return None

            try:
                os.remove(destination_path)
            except OSError:
                pass

            os.rename(temp_path, destination_path)
            print("WAV descargado correctamente:", bytes_written, "bytes")
            gc.collect()
            print("Heap después HTTPS audio:", gc.mem_free())
            return destination_path
        except Exception as exc:
            print("Error de conexion HTTP al descargar audio:", exc)
            return None
        finally:
            try:
                if output_file is not None:
                    output_file.close()
            except Exception:
                pass

            try:
                if response is not None:
                    response.close()
            except Exception:
                pass

            try:
                os.remove(temp_path)
            except OSError:
                pass

            gc.collect()
