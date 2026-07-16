"""HTTP communication service for the ESP32 MicroPython application."""

import urequests

from config import BACKEND_HOST, BACKEND_PORT


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
                return response.json()
            except Exception as exc:
                print("Error al procesar JSON de la respuesta:", exc)
                return None
        finally:
            try:
                response.close()
            except Exception:
                pass
