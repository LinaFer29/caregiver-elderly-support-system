from machine import Pin, I2S, DAC, SoftI2C
from time import sleep_ms, ticks_ms, ticks_us, ticks_add, ticks_diff
import gc
import json
import machine
import network
import os
import socket
import struct

# ============================================================
# FLUJO COMPLETO DE PRUEBA
#
# 1. Graba 3 segundos con el INMP441.
# 2. Envía PCM16 crudo a POST /assistant/stt/.
# 3. Lee el JSON y obtiene "audio_file".
# 4. Descarga GET /assistant/audio/<audio_file>/.
# 5. Guarda temporalmente el WAV en la memoria flash.
# 6. Reproduce el WAV por el DAC GPIO25 -> PAM8403.
# 7. Reinicia el ESP32 para liberar I2S y DAC.
#
# NO guardar este archivo como main.py durante las pruebas.
# ============================================================

# -------------------------- RED -------------------------------

WIFI_SSID = "ENZO"
WIFI_PASSWORD = "20041229"

# IP LAN del computador donde se ejecuta Django.
BACKEND_HOST = "192.168.1.54"
BACKEND_PORT = 8000

STT_PATH = "/assistant/stt/"
AUDIO_PATH_PREFIX = "/assistant/audio/"

# Tiempos máximos de espera del socket.
# El POST puede tardar mientras Whisper transcribe e interpreta.
TIMEOUT_CONEXION_SEGUNDOS = 15
TIMEOUT_ENVIO_SEGUNDOS = 30
TIMEOUT_STT_SEGUNDOS = 120

# Durante la descarga del WAV usamos un timeout corto por lectura,
# pero permitimos varios timeouts consecutivos antes de abortar.
TIMEOUT_LECTURA_AUDIO_SEGUNDOS = 8
MAX_TIMEOUTS_AUDIO_CONSECUTIVOS = 8

# ------------------------ HARDWARE ----------------------------

# INMP441 comprobado en tu montaje.
MIC_SCK = 14
MIC_WS = 27
MIC_SD = 32

# DAC interno conectado al PAM8403.
PIN_AUDIO = 25

# OLED integrado.
OLED_SDA = 21
OLED_SCL = 22

# ------------------------- AUDIO ------------------------------

SAMPLE_RATE = 16000
SEGUNDOS_GRABACION = 3

RAW_BUFFER_BYTES = 1024
PCM_CHUNK_BYTES = RAW_BUFFER_BYTES // 2
TOTAL_PCM_BYTES = SAMPLE_RATE * SEGUNDOS_GRABACION * 2

# El DAC se manejará hasta aproximadamente 8 kHz desde Python.
# Si el WAV es 16 kHz se conserva una muestra de cada dos.
MAX_DAC_RATE = 8000

# Volumen digital enviado al PAM8403.
# El amplificador tiene ganancia alta, por eso comenzamos al 20 %.
# Prueba después con 25, 30 o 35; no empieces en 100.
VOLUMEN_PORCENTAJE = 4

ARCHIVO_WAV_TEMPORAL = "/respuesta_backend.wav"
LIMITE_JSON_BYTES = 16000


# ============================================================
# OLED
# ============================================================

def iniciar_oled():
    try:
        import ssd1306

        i2c = SoftI2C(
            scl=Pin(OLED_SCL),
            sda=Pin(OLED_SDA),
            freq=400000
        )

        if 60 not in i2c.scan():
            return None

        return ssd1306.SSD1306_I2C(
            128,
            64,
            i2c,
            addr=0x3C
        )

    except Exception as error:
        print("OLED no disponible:", error)
        return None


def mostrar(oled, lineas):
    if oled is None:
        return

    oled.fill(0)

    for indice, texto in enumerate(lineas[:8]):
        oled.text(str(texto)[:16], 0, indice * 8)

    oled.show()


# ============================================================
# WI-FI
# ============================================================

def interfaz_wifi_estacion():
    try:
        return network.WLAN(network.WLAN.IF_STA)
    except AttributeError:
        return network.WLAN(network.STA_IF)


def configurar_wifi_para_transferencias(wlan):
    """
    Desactiva el ahorro de energía Wi-Fi cuando el firmware lo permite.
    Esto ayuda a evitar pausas largas durante descargas sostenidas.
    """
    try:
        wlan.config(pm=wlan.PM_NONE)
        print("Ahorro de energía Wi-Fi desactivado.")
        return
    except (AttributeError, OSError, ValueError):
        pass

    try:
        wlan.config(pm=network.WLAN.PM_NONE)
        print("Ahorro de energía Wi-Fi desactivado.")
    except (AttributeError, OSError, ValueError):
        print("El firmware no permite cambiar el modo de energía Wi-Fi.")


def conectar_wifi(oled, timeout_ms=20000):
    wlan = interfaz_wifi_estacion()
    wlan.active(True)

    if wlan.isconnected():
        configurar_wifi_para_transferencias(wlan)
        print("Wi-Fi ya conectado:", wlan.ifconfig())
        return wlan

    mostrar(oled, ["CONECTANDO WIFI", WIFI_SSID])
    print("Conectando a Wi-Fi:", WIFI_SSID)

    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    inicio = ticks_ms()

    while not wlan.isconnected():
        if ticks_diff(ticks_ms(), inicio) > timeout_ms:
            raise RuntimeError("Tiempo agotado conectando al Wi-Fi")

        sleep_ms(250)

    configurar_wifi_para_transferencias(wlan)

    print("Wi-Fi conectado:", wlan.ifconfig())
    mostrar(oled, ["WIFI CONECTADO", wlan.ifconfig()[0]])

    return wlan


# ============================================================
# HTTP POR SOCKET
# ============================================================

def configurar_timeout(cliente, segundos):
    try:
        cliente.settimeout(segundos)
    except AttributeError:
        pass


def abrir_socket_http():
    direccion = socket.getaddrinfo(
        BACKEND_HOST,
        BACKEND_PORT,
        0,
        socket.SOCK_STREAM
    )[0][-1]

    cliente = socket.socket()

    configurar_timeout(
        cliente,
        TIMEOUT_CONEXION_SEGUNDOS
    )

    cliente.connect(direccion)

    configurar_timeout(
        cliente,
        TIMEOUT_ENVIO_SEGUNDOS
    )

    return cliente


def escribir_completo(cliente, datos):
    vista = memoryview(datos)
    enviados = 0

    while enviados < len(vista):
        cantidad = cliente.write(vista[enviados:])

        # Algunas implementaciones bloqueantes devuelven None
        # después de aceptar todo el bloque.
        if cantidad is None:
            return

        if cantidad <= 0:
            raise OSError("El socket dejó de aceptar datos")

        enviados += cantidad


def leer_exacto(cliente, cantidad):
    datos = bytearray(cantidad)
    vista = memoryview(datos)
    recibidos = 0

    while recibidos < cantidad:
        bloque = cliente.recv(cantidad - recibidos)

        if not bloque:
            raise OSError("La conexión terminó antes de tiempo")

        vista[recibidos:recibidos + len(bloque)] = bloque
        recibidos += len(bloque)

    return datos


def leer_estado_y_cabeceras(cliente):
    linea_estado = cliente.readline()

    if not linea_estado:
        raise OSError("El servidor no devolvió una respuesta HTTP")

    linea_estado = linea_estado.decode("utf-8", "replace").strip()
    partes = linea_estado.split()

    if len(partes) < 2:
        raise ValueError("Línea HTTP inválida: " + linea_estado)

    codigo = int(partes[1])
    cabeceras = {}

    while True:
        linea = cliente.readline()

        if not linea or linea in (b"\r\n", b"\n"):
            break

        texto = linea.decode("utf-8", "replace").strip()

        if ":" in texto:
            nombre, valor = texto.split(":", 1)
            cabeceras[nombre.strip().lower()] = valor.strip()

    return linea_estado, codigo, cabeceras


def leer_cuerpo_pequeno(cliente, cabeceras, limite=LIMITE_JSON_BYTES):
    """
    Lee respuestas pequeñas, por ejemplo el JSON de /assistant/stt/.
    Soporta Content-Length, chunked y cierre de conexión.
    """
    resultado = bytearray()
    transferencia = cabeceras.get("transfer-encoding", "").lower()

    if "chunked" in transferencia:
        while True:
            linea_tamano = cliente.readline()

            if not linea_tamano:
                raise OSError("Respuesta chunked incompleta")

            parte_hex = linea_tamano.strip().split(b";", 1)[0]
            tamano = int(parte_hex, 16)

            if tamano == 0:
                # Consumir trailers hasta la línea vacía.
                while True:
                    trailer = cliente.readline()
                    if not trailer or trailer in (b"\r\n", b"\n"):
                        break
                break

            bloque = leer_exacto(cliente, tamano)

            if len(resultado) + len(bloque) > limite:
                raise MemoryError("La respuesta JSON supera el límite")

            resultado.extend(bloque)
            leer_exacto(cliente, 2)  # CRLF

        return bytes(resultado)

    if "content-length" in cabeceras:
        tamano = int(cabeceras["content-length"])

        if tamano > limite:
            raise MemoryError("La respuesta JSON supera el límite")

        return bytes(leer_exacto(cliente, tamano))

    while len(resultado) < limite:
        bloque = cliente.recv(min(512, limite - len(resultado)))

        if not bloque:
            break

        resultado.extend(bloque)

    return bytes(resultado)


def guardar_cuerpo_en_archivo(cliente, cabeceras, ruta):
    """
    Descarga el cuerpo HTTP directamente a flash.

    Un OSError(116) es un timeout de lectura. No se aborta en el primer
    timeout: se vuelve a intentar mientras el servidor siga enviando
    datos. El contador se reinicia cada vez que llega un bloque.
    """
    transferencia = cabeceras.get("transfer-encoding", "").lower()
    longitud_texto = cabeceras.get("content-length")
    total = 0
    timeouts_consecutivos = 0
    proximo_reporte = 16384

    def recibir_con_reintentos(tamano):
        nonlocal timeouts_consecutivos

        while True:
            try:
                bloque = cliente.recv(tamano)

                # Llegó información o cierre limpio: reiniciar contador.
                timeouts_consecutivos = 0
                return bloque

            except OSError as error:
                codigo = error.args[0] if error.args else None

                if codigo in (104, 54):
                    # Reinicio de conexión.
                    return None

                if codigo == 116:
                    timeouts_consecutivos += 1

                    print(
                        "Pausa de red durante la descarga:",
                        timeouts_consecutivos,
                        "de",
                        MAX_TIMEOUTS_AUDIO_CONSECUTIVOS
                    )

                    if (
                        timeouts_consecutivos
                        >= MAX_TIMEOUTS_AUDIO_CONSECUTIVOS
                    ):
                        raise RuntimeError(
                            "La descarga no recibió datos durante "
                            "aproximadamente {} segundos. "
                            "Se habían recibido {} bytes.".format(
                                TIMEOUT_LECTURA_AUDIO_SEGUNDOS
                                * MAX_TIMEOUTS_AUDIO_CONSECUTIVOS,
                                total
                            )
                        )

                    sleep_ms(100)
                    continue

                raise

    with open(ruta, "wb") as archivo:
        if "chunked" in transferencia:
            while True:
                linea_tamano = cliente.readline()

                if not linea_tamano:
                    raise OSError("Descarga chunked incompleta")

                parte_hex = linea_tamano.strip().split(b";", 1)[0]
                restante_chunk = int(parte_hex, 16)

                if restante_chunk == 0:
                    while True:
                        trailer = cliente.readline()

                        if not trailer or trailer in (b"\r\n", b"\n"):
                            break

                    break

                while restante_chunk > 0:
                    bloque = recibir_con_reintentos(
                        min(1024, restante_chunk)
                    )

                    if bloque is None:
                        raise OSError(
                            "Conexión reiniciada dentro de un chunk. "
                            "Faltaban {} bytes.".format(restante_chunk)
                        )

                    if not bloque:
                        raise OSError(
                            "El WAV terminó antes de completar un chunk"
                        )

                    archivo.write(bloque)
                    total += len(bloque)
                    restante_chunk -= len(bloque)

                    if total >= proximo_reporte:
                        print("Descargados:", total, "bytes")
                        proximo_reporte += 16384

                leer_exacto(cliente, 2)

            return total

        if longitud_texto is not None:
            esperado = int(longitud_texto)
            restante = esperado

            while restante > 0:
                bloque = recibir_con_reintentos(
                    min(1024, restante)
                )

                if bloque is None:
                    raise OSError(
                        "La conexión se reinició antes de completar "
                        "el WAV. Recibidos {} de {} bytes.".format(
                            total,
                            esperado
                        )
                    )

                if not bloque:
                    raise OSError(
                        "El servidor cerró antes de completar el WAV. "
                        "Recibidos {} de {} bytes.".format(
                            total,
                            esperado
                        )
                    )

                archivo.write(bloque)
                total += len(bloque)
                restante -= len(bloque)

                if total >= proximo_reporte:
                    porcentaje = total * 100 // esperado

                    print(
                        "Descargados:",
                        total,
                        "de",
                        esperado,
                        "bytes -",
                        porcentaje,
                        "%"
                    )

                    proximo_reporte += 16384

            return total

        while True:
            bloque = recibir_con_reintentos(1024)

            if bloque is None:
                if total == 0:
                    raise OSError(
                        "La conexión se reinició sin recibir el WAV"
                    )

                print(
                    "Aviso: la conexión terminó con ECONNRESET "
                    "después de {} bytes.".format(total)
                )
                break

            if not bloque:
                break

            archivo.write(bloque)
            total += len(bloque)

            if total >= proximo_reporte:
                print("Descargados:", total, "bytes")
                proximo_reporte += 16384

    return total


# ============================================================
# POST STT: GRABAR Y ENVIAR PCM16
# ============================================================

def enviar_stt_streaming(oled):
    gc.collect()

    cliente = None
    microfono = None

    raw = bytearray(RAW_BUFFER_BYTES)
    pcm = bytearray(PCM_CHUNK_BYTES)

    enviados_audio = 0
    pico_maximo = 0

    try:
        cliente = abrir_socket_http()

        encabezado = (
            "POST {} HTTP/1.1\r\n"
            "Host: {}:{}\r\n"
            "Content-Type: application/octet-stream\r\n"
            "Content-Length: {}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).format(
            STT_PATH,
            BACKEND_HOST,
            BACKEND_PORT,
            TOTAL_PCM_BYTES
        ).encode()

        escribir_completo(cliente, encabezado)

        microfono = I2S(
            0,
            sck=Pin(MIC_SCK),
            ws=Pin(MIC_WS),
            sd=Pin(MIC_SD),
            mode=I2S.RX,
            bits=32,
            format=I2S.MONO,
            rate=SAMPLE_RATE,
            ibuf=20000
        )

        mostrar(oled, [
            "GRABANDO",
            "{} SEGUNDOS".format(SEGUNDOS_GRABACION),
            "Y ENVIANDO...",
            "",
            "HABLE AHORA"
        ])

        print()
        print("GRABANDO Y ENVIANDO...")
        print("Bytes esperados:", TOTAL_PCM_BYTES)

        while enviados_audio < TOTAL_PCM_BYTES:
            bytes_leidos = microfono.readinto(raw)

            if not bytes_leidos:
                continue

            muestras_disponibles = bytes_leidos // 4
            bytes_pcm_disponibles = muestras_disponibles * 2
            bytes_restantes = TOTAL_PCM_BYTES - enviados_audio

            bytes_pcm_a_enviar = min(
                bytes_pcm_disponibles,
                bytes_restantes
            )

            muestras_a_convertir = bytes_pcm_a_enviar // 2
            posicion_pcm = 0

            for indice in range(muestras_a_convertir):
                posicion_raw = indice * 4

                muestra_32 = struct.unpack_from(
                    "<i",
                    raw,
                    posicion_raw
                )[0]

                muestra_16 = muestra_32 >> 16

                struct.pack_into(
                    "<h",
                    pcm,
                    posicion_pcm,
                    muestra_16
                )

                absoluto = abs(muestra_16)

                if absoluto > pico_maximo:
                    pico_maximo = absoluto

                posicion_pcm += 2

            escribir_completo(
                cliente,
                memoryview(pcm)[:bytes_pcm_a_enviar]
            )

            enviados_audio += bytes_pcm_a_enviar

        microfono.deinit()
        microfono = None
        sleep_ms(150)

        print("Audio enviado:", enviados_audio, "bytes")
        print("Pico PCM16:", pico_maximo)

        # La transcripción e interpretación pueden tardar más de
        # 25 segundos. Dar un tiempo distinto para esta respuesta.
        configurar_timeout(
            cliente,
            TIMEOUT_STT_SEGUNDOS
        )

        print(
            "Esperando respuesta STT "
            "(máximo {} segundos)...".format(
                TIMEOUT_STT_SEGUNDOS
            )
        )

        inicio_espera_stt = ticks_ms()

        try:
            linea, codigo, cabeceras = leer_estado_y_cabeceras(
                cliente
            )
            cuerpo = leer_cuerpo_pequeno(
                cliente,
                cabeceras
            )
        except OSError as error:
            codigo_error = (
                error.args[0]
                if error.args
                else None
            )

            if codigo_error == 116:
                raise RuntimeError(
                    "Tiempo agotado esperando la respuesta de "
                    "/assistant/stt/ después de {} segundos. "
                    "El audio sí fue enviado; revisa cuánto tarda "
                    "Whisper en el backend.".format(
                        TIMEOUT_STT_SEGUNDOS
                    )
                )

            raise

        tiempo_stt_ms = ticks_diff(
            ticks_ms(),
            inicio_espera_stt
        )

        print(
            "Respuesta STT recibida después de",
            tiempo_stt_ms,
            "ms"
        )

        print("Respuesta STT:", linea)
        print(cuerpo.decode("utf-8", "replace"))

        if codigo < 200 or codigo >= 300:
            raise RuntimeError(
                "El endpoint STT respondió HTTP {}".format(codigo)
            )

        respuesta_json = json.loads(
            cuerpo.decode("utf-8")
        )

        return respuesta_json

    finally:
        if microfono is not None:
            try:
                microfono.deinit()
            except Exception:
                pass

        if cliente is not None:
            try:
                cliente.close()
            except Exception:
                pass

        del raw
        del pcm
        gc.collect()


# ============================================================
# DESCARGAR EL WAV
# ============================================================

def codificar_segmento_url(texto):
    """
    Codificación porcentual mínima para un nombre de archivo.
    Se permiten letras, números, punto, guion y guion bajo.
    """
    permitidos = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        "-_.~"
    )

    resultado = ""

    for caracter in texto:
        if caracter in permitidos:
            resultado += caracter
        else:
            for byte in caracter.encode("utf-8"):
                resultado += "%{:02X}".format(byte)

    return resultado


def validar_nombre_archivo(nombre):
    if not isinstance(nombre, str) or not nombre:
        raise ValueError("audio_file no contiene un nombre válido")

    # El endpoint debe recibir solamente un nombre, no una ruta.
    if "/" in nombre or "\\" in nombre or ".." in nombre:
        raise ValueError("Nombre de audio no permitido: " + nombre)

    if not nombre.lower().endswith(".wav"):
        raise ValueError("El backend no devolvió un archivo .wav")

    return nombre


def descargar_wav(nombre_archivo, oled):
    nombre_archivo = validar_nombre_archivo(nombre_archivo)
    nombre_url = codificar_segmento_url(nombre_archivo)

    ruta_http = (
        AUDIO_PATH_PREFIX
        + nombre_url
        + "/"
    )

    cliente = None

    try:
        mostrar(oled, [
            "DESCARGANDO WAV",
            nombre_archivo[:16]
        ])

        print()
        print("Descargando:", ruta_http)

        cliente = abrir_socket_http()

        peticion = (
            "GET {} HTTP/1.1\r\n"
            "Host: {}:{}\r\n"
            "Accept: */*\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).format(
            ruta_http,
            BACKEND_HOST,
            BACKEND_PORT
        ).encode()

        escribir_completo(cliente, peticion)

        configurar_timeout(
            cliente,
            TIMEOUT_LECTURA_AUDIO_SEGUNDOS
        )

        print(
            "Esperando archivo WAV..."
        )
        print(
            "Timeout por lectura:",
            TIMEOUT_LECTURA_AUDIO_SEGUNDOS,
            "s; reintentos:",
            MAX_TIMEOUTS_AUDIO_CONSECUTIVOS
        )

        linea, codigo, cabeceras = leer_estado_y_cabeceras(cliente)
        print("Respuesta audio:", linea)
        print("Cabeceras audio:")

        for nombre, valor in cabeceras.items():
            print(" ", nombre, ":", valor)

        if codigo < 200 or codigo >= 300:
            cuerpo_error = leer_cuerpo_pequeno(
                cliente,
                cabeceras,
                limite=4000
            )

            raise RuntimeError(
                "GET audio HTTP {}: {}".format(
                    codigo,
                    cuerpo_error.decode("utf-8", "replace")
                )
            )

        try:
            os.remove(ARCHIVO_WAV_TEMPORAL)
        except OSError:
            pass

        bytes_guardados = guardar_cuerpo_en_archivo(
            cliente,
            cabeceras,
            ARCHIVO_WAV_TEMPORAL
        )

        print(
            "WAV guardado:",
            ARCHIVO_WAV_TEMPORAL,
            "-",
            bytes_guardados,
            "bytes"
        )

        mostrar(oled, [
            "WAV DESCARGADO",
            "{} BYTES".format(bytes_guardados),
            "",
            "VALIDANDO..."
        ])

        return ARCHIVO_WAV_TEMPORAL

    finally:
        if cliente is not None:
            try:
                cliente.close()
            except Exception:
                pass

        gc.collect()


# ============================================================
# LEER Y REPRODUCIR WAV
# ============================================================

def leer_informacion_wav(ruta):
    with open(ruta, "rb") as archivo:
        cabecera = archivo.read(12)

        if len(cabecera) != 12:
            raise ValueError("Archivo WAV demasiado pequeño")

        if cabecera[0:4] != b"RIFF":
            raise ValueError("El archivo no comienza con RIFF")

        if cabecera[8:12] != b"WAVE":
            raise ValueError("El archivo no contiene WAVE")

        formato = None
        posicion_datos = None
        tamano_datos = None

        while True:
            cabecera_chunk = archivo.read(8)

            if len(cabecera_chunk) < 8:
                break

            identificador = cabecera_chunk[0:4]
            tamano_chunk = struct.unpack(
                "<I",
                cabecera_chunk[4:8]
            )[0]

            if identificador == b"fmt ":
                if tamano_chunk < 16:
                    raise ValueError("Chunk fmt inválido")

                datos_fmt = archivo.read(tamano_chunk)

                if len(datos_fmt) != tamano_chunk:
                    raise ValueError("Chunk fmt incompleto")

                formato_audio = struct.unpack_from("<H", datos_fmt, 0)[0]
                canales = struct.unpack_from("<H", datos_fmt, 2)[0]
                frecuencia = struct.unpack_from("<I", datos_fmt, 4)[0]
                bytes_por_segundo = struct.unpack_from("<I", datos_fmt, 8)[0]
                alineacion = struct.unpack_from("<H", datos_fmt, 12)[0]
                bits = struct.unpack_from("<H", datos_fmt, 14)[0]

                formato = {
                    "formato_audio": formato_audio,
                    "canales": canales,
                    "frecuencia": frecuencia,
                    "bytes_por_segundo": bytes_por_segundo,
                    "alineacion": alineacion,
                    "bits": bits
                }

                if tamano_chunk & 1:
                    archivo.read(1)

            elif identificador == b"data":
                posicion_datos = archivo.tell()
                tamano_datos = tamano_chunk
                break

            else:
                archivo.seek(
                    tamano_chunk + (tamano_chunk & 1),
                    1
                )

        if formato is None:
            raise ValueError("El WAV no contiene chunk fmt")

        if posicion_datos is None:
            raise ValueError("El WAV no contiene chunk data")

        return {
            "formato_audio": formato["formato_audio"],
            "canales": formato["canales"],
            "frecuencia": formato["frecuencia"],
            "bytes_por_segundo": formato["bytes_por_segundo"],
            "alineacion": formato["alineacion"],
            "bits": formato["bits"],
            "posicion_datos": posicion_datos,
            "tamano_datos": tamano_datos
        }


def validar_wav(info):
    # 1 significa PCM lineal sin compresión.
    if info["formato_audio"] != 1:
        raise ValueError(
            "WAV no compatible: formato {}, se requiere PCM".format(
                info["formato_audio"]
            )
        )

    if info["bits"] not in (8, 16):
        raise ValueError(
            "WAV no compatible: {} bits; se permiten 8 o 16".format(
                info["bits"]
            )
        )

    if info["canales"] not in (1, 2):
        raise ValueError(
            "WAV no compatible: {} canales".format(
                info["canales"]
            )
        )

    bytes_por_muestra = info["bits"] // 8
    alineacion_esperada = info["canales"] * bytes_por_muestra

    if info["alineacion"] != alineacion_esperada:
        raise ValueError(
            "Alineación WAV inesperada: {}".format(
                info["alineacion"]
            )
        )


def leer_pcm16_le(buffer, posicion):
    valor = buffer[posicion] | (buffer[posicion + 1] << 8)

    if valor >= 32768:
        valor -= 65536

    return valor


def crear_tabla_volumen():
    """
    Tabla de 256 posiciones para reducir el volumen sin hacer
    multiplicaciones dentro del bucle de reproducción.
    """
    tabla = bytearray(256)

    for valor in range(256):
        centrado = valor - 128
        ajustado = 128 + (
            centrado * VOLUMEN_PORCENTAJE // 100
        )

        if ajustado < 0:
            ajustado = 0
        elif ajustado > 255:
            ajustado = 255

        tabla[valor] = ajustado

    return tabla


def reproducir_pcm_u8_8k(ruta, info, oled):
    """
    Ruta recomendada:
      WAV PCM
      8 bits unsigned
      mono
      8000 Hz

    El byte del WAV ya tiene el mismo rango 0..255 que necesita
    el DAC del ESP32. Solo aplicamos una tabla de volumen.
    """
    if info["canales"] != 1:
        raise ValueError(
            "Para reproducción clara en 8 bits, el WAV debe ser mono"
        )

    if info["frecuencia"] != 8000:
        raise ValueError(
            "Para la ruta optimizada, el WAV debe estar a 8000 Hz"
        )

    periodo_us = 125  # 1.000.000 / 8.000
    tabla_volumen = crear_tabla_volumen()
    buffer_audio = bytearray(1024)

    dac = DAC(Pin(PIN_AUDIO))
    dac.write(128)

    muestras_reproducidas = 0
    siguiente_instante = ticks_us()

    gc.collect()
    print("Memoria libre antes de reproducir:", gc.mem_free())
    print("Volumen digital:", VOLUMEN_PORCENTAJE, "%")

    try:
        with open(ruta, "rb") as archivo:
            archivo.seek(info["posicion_datos"])
            restantes = info["tamano_datos"]

            gc.disable()

            while restantes > 0:
                cantidad_objetivo = min(
                    len(buffer_audio),
                    restantes
                )

                vista = memoryview(buffer_audio)[:cantidad_objetivo]
                bytes_leidos = archivo.readinto(vista)

                if not bytes_leidos:
                    break

                indice = 0

                # La lectura desde flash puede retrasar el reloj.
                if ticks_diff(
                    siguiente_instante,
                    ticks_us()
                ) < -(periodo_us * 4):
                    siguiente_instante = ticks_us()

                while indice < bytes_leidos:
                    dac.write(
                        tabla_volumen[buffer_audio[indice]]
                    )

                    siguiente_instante = ticks_add(
                        siguiente_instante,
                        periodo_us
                    )

                    while ticks_diff(
                        siguiente_instante,
                        ticks_us()
                    ) > 0:
                        pass

                    indice += 1
                    muestras_reproducidas += 1

                restantes -= bytes_leidos

    finally:
        gc.enable()

        try:
            dac.write(128)
        except Exception:
            pass

        sleep_ms(100)

        try:
            dac.deinit()
        except (AttributeError, OSError):
            pass

        del buffer_audio
        del tabla_volumen
        gc.collect()

    if muestras_reproducidas != info["tamano_datos"]:
        raise RuntimeError(
            "Audio incompleto: {} de {} muestras".format(
                muestras_reproducidas,
                info["tamano_datos"]
            )
        )

    print(
        "Reproducción terminada:",
        muestras_reproducidas,
        "muestras."
    )


def reproducir_pcm16_compatible(ruta, info, oled):
    """
    Ruta de compatibilidad para WAV PCM16.

    Se mantiene para pruebas, pero la mejor calidad con el DAC desde
    MicroPython se obtiene preparando el archivo como PCM U8, mono,
    8000 Hz en el backend.
    """
    factor_salto = (
        info["frecuencia"] + MAX_DAC_RATE - 1
    ) // MAX_DAC_RATE

    if factor_salto < 1:
        factor_salto = 1

    frecuencia_salida = (
        info["frecuencia"] // factor_salto
    )

    periodo_us = 1000000 // frecuencia_salida
    bytes_por_frame = info["canales"] * 2
    frames_totales = info["tamano_datos"] // bytes_por_frame

    print("  Factor de reducción:", factor_salto)
    print("  Frecuencia DAC:", frecuencia_salida, "Hz")
    print(
        "  AVISO: convierta el WAV a PCM U8 mono 8000 Hz "
        "para mejorar claridad."
    )

    dac = DAC(Pin(PIN_AUDIO))
    dac.write(128)

    buffer_audio = bytearray(2048)
    tabla_volumen = crear_tabla_volumen()

    frames_procesados = 0
    indice_global = 0
    siguiente_instante = ticks_us()

    gc.collect()

    try:
        with open(ruta, "rb") as archivo:
            archivo.seek(info["posicion_datos"])
            bytes_restantes = info["tamano_datos"]

            gc.disable()

            while bytes_restantes > 0:
                bytes_leidos = archivo.readinto(buffer_audio)

                if not bytes_leidos:
                    break

                bytes_validos = min(
                    bytes_leidos,
                    bytes_restantes
                )

                bytes_validos -= (
                    bytes_validos % bytes_por_frame
                )

                if bytes_validos <= 0:
                    break

                frames_bloque = (
                    bytes_validos // bytes_por_frame
                )

                frame = 0

                if ticks_diff(
                    siguiente_instante,
                    ticks_us()
                ) < -(periodo_us * 4):
                    siguiente_instante = ticks_us()

                while frame < frames_bloque:
                    if indice_global % factor_salto == 0:
                        posicion = frame * bytes_por_frame

                        izquierda = leer_pcm16_le(
                            buffer_audio,
                            posicion
                        )

                        if info["canales"] == 2:
                            derecha = leer_pcm16_le(
                                buffer_audio,
                                posicion + 2
                            )
                            muestra = (izquierda + derecha) // 2
                        else:
                            muestra = izquierda

                        # Convertir PCM16 signed a U8.
                        muestra_u8 = 128 + (muestra >> 8)

                        if muestra_u8 < 0:
                            muestra_u8 = 0
                        elif muestra_u8 > 255:
                            muestra_u8 = 255

                        dac.write(tabla_volumen[muestra_u8])

                        siguiente_instante = ticks_add(
                            siguiente_instante,
                            periodo_us
                        )

                        while ticks_diff(
                            siguiente_instante,
                            ticks_us()
                        ) > 0:
                            pass

                    indice_global += 1
                    frame += 1

                frames_procesados += frames_bloque
                bytes_restantes -= bytes_validos

    finally:
        gc.enable()

        try:
            dac.write(128)
        except Exception:
            pass

        sleep_ms(100)

        try:
            dac.deinit()
        except (AttributeError, OSError):
            pass

        del buffer_audio
        del tabla_volumen
        gc.collect()

    if frames_procesados < frames_totales:
        raise RuntimeError(
            "El WAV no se reprodujo completo: {} de {} frames".format(
                frames_procesados,
                frames_totales
            )
        )


def reproducir_wav(ruta, oled):
    info = leer_informacion_wav(ruta)
    validar_wav(info)

    print()
    print("Información WAV:")
    print("  PCM:", info["formato_audio"])
    print("  Canales:", info["canales"])
    print("  Frecuencia:", info["frecuencia"], "Hz")
    print("  Bits:", info["bits"])
    print("  Datos:", info["tamano_datos"], "bytes")

    mostrar(oled, [
        "REPRODUCIENDO",
        "{} HZ".format(info["frecuencia"]),
        "{} BITS".format(info["bits"]),
        "{} CANAL".format(info["canales"])
    ])

    if (
        info["bits"] == 8
        and info["canales"] == 1
        and info["frecuencia"] == 8000
    ):
        print("Usando reproducción optimizada PCM U8 / 8 kHz.")
        reproducir_pcm_u8_8k(
            ruta,
            info,
            oled
        )
    else:
        print("Usando reproducción de compatibilidad PCM16.")
        reproducir_pcm16_compatible(
            ruta,
            info,
            oled
        )

    print("Memoria libre después de reproducir:", gc.mem_free())

    mostrar(oled, [
        "AUDIO TERMINADO",
        "",
        "RESPUESTA OK"
    ])


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

oled = iniciar_oled()

try:
    mostrar(oled, [
        "ASISTENTE",
        "PREPARANDO..."
    ])

    conectar_wifi(oled)
    sleep_ms(500)

    respuesta = enviar_stt_streaming(oled)

    print()
    print("JSON interpretado:")
    print(respuesta)

    transcripcion = respuesta.get("transcription", "")
    texto_respuesta = respuesta.get("response_text", "")
    nombre_audio = respuesta.get("audio_file")

    print("Transcripción:", transcripcion)
    print("Respuesta:", texto_respuesta)
    print("Audio:", nombre_audio)

    mostrar(oled, [
        "STT OK",
        transcripcion[:16],
        "",
        "RESPUESTA",
        texto_respuesta[:16]
    ])

    if not nombre_audio:
        raise ValueError(
            "La respuesta JSON no contiene audio_file"
        )

    ruta_wav = descargar_wav(nombre_audio, oled)
    reproducir_wav(ruta_wav, oled)

    print()
    print("Flujo completo terminado correctamente.")

except Exception as error:
    print()
    print("ERROR:", repr(error))

    mostrar(oled, [
        "ERROR",
        str(error)[:16],
        str(error)[16:32],
        str(error)[32:48]
    ])

finally:
    # No hacemos machine.reset() automáticamente porque el reinicio
    # puede coincidir con el momento en que Thonny comienza a enviar
    # otra ejecución mediante raw-paste.
    print()
    print("Programa terminado.")
    print("Antes de ejecutarlo otra vez:")
    print("1. Presiona el botón EN del ESP32.")
    print("2. Espera a que aparezca >>>.")
    print("3. Después presiona F5.")