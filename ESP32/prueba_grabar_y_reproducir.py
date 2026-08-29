from machine import Pin, I2S, DAC, SoftI2C
from time import sleep_ms, ticks_us, ticks_add, ticks_diff
import machine
import struct
import gc

# ============================================================
# PRUEBA REINICIABLE: GRABAR 2 SEGUNDOS Y REPRODUCIR
#
# IMPORTANTE:
# - El DAC se crea solamente después de cerrar I2S.
# - Al terminar, se hace un reinicio físico mediante machine.reset()
#   para liberar completamente el DAC de GPIO25.
# - Ejecútalo desde Thonny. No lo guardes como main.py.
# ============================================================

MIC_SCK = 14
MIC_WS = 27
MIC_SD = 32
PIN_AUDIO = 25

FRECUENCIA_MIC = 16000
FRECUENCIA_REPRODUCCION = 8000
SEGUNDOS = 2
DIVISOR_GANANCIA = 8192

MUESTRAS_SALIDA = FRECUENCIA_REPRODUCCION * SEGUNDOS
audio = bytearray(MUESTRAS_SALIDA)
buffer_i2s = bytearray(1024)


def iniciar_oled():
    try:
        import ssd1306
        i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=400000)

        if 60 not in i2c.scan():
            return None

        return ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)

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


oled = iniciar_oled()
microfono = None
dac = None

try:
    print()
    print("=== PRUEBA REINICIABLE DE AUDIO ===")
    print("Habla cuando la pantalla muestre GRABANDO.")

    mostrar(oled, [
        "PRUEBA AUDIO",
        "PREPARANDO...",
        "HABLE CUANDO",
        "DIGA GRABANDO"
    ])

    sleep_ms(1500)

    # --------------------------------------------------------
    # 1. GRABACIÓN: se utiliza I2S y todavía NO se crea el DAC.
    # --------------------------------------------------------
    microfono = I2S(
        0,
        sck=Pin(MIC_SCK),
        ws=Pin(MIC_WS),
        sd=Pin(MIC_SD),
        mode=I2S.RX,
        bits=32,
        format=I2S.MONO,
        rate=FRECUENCIA_MIC,
        ibuf=20000
    )

    mostrar(oled, [
        "GRABANDO 2 SEG",
        "HABLE AHORA",
        "",
        "SCK 14",
        "WS  27",
        "SD  32"
    ])

    print("GRABANDO: habla ahora...")

    indice_salida = 0
    contador_entrada = 0
    pico_maximo = 0

    while indice_salida < MUESTRAS_SALIDA:
        bytes_leidos = microfono.readinto(buffer_i2s)

        if not bytes_leidos:
            continue

        for posicion in range(0, bytes_leidos - 3, 4):
            muestra = struct.unpack_from("<i", buffer_i2s, posicion)[0] >> 8

            absoluto = abs(muestra)
            if absoluto > pico_maximo:
                pico_maximo = absoluto

            # Conserva una de cada dos muestras:
            # 16 kHz de entrada -> 8 kHz de salida.
            if contador_entrada % 2 == 0:
                valor_dac = 128 + (muestra // DIVISOR_GANANCIA)

                if valor_dac < 0:
                    valor_dac = 0
                elif valor_dac > 255:
                    valor_dac = 255

                audio[indice_salida] = valor_dac
                indice_salida += 1

                if indice_salida >= MUESTRAS_SALIDA:
                    break

            contador_entrada += 1

    # Cerrar I2S antes de reservar el DAC.
    microfono.deinit()
    microfono = None
    sleep_ms(150)

    print("Grabación terminada.")
    print("Pico máximo capturado:", pico_maximo)

    mostrar(oled, [
        "GRABACION OK",
        "PICO:",
        str(pico_maximo),
        "",
        "REPRODUCIENDO"
    ])

    sleep_ms(700)

    # --------------------------------------------------------
    # 2. REPRODUCCIÓN: ahora sí se crea el DAC.
    # --------------------------------------------------------
    print("REPRODUCIENDO...")
    dac = DAC(Pin(PIN_AUDIO))
    dac.write(128)

    periodo_us = 1000000 // FRECUENCIA_REPRODUCCION
    proximo_instante = ticks_us()

    gc.collect()
    gc.disable()

    try:
        for valor in audio:
            dac.write(valor)
            proximo_instante = ticks_add(proximo_instante, periodo_us)

            while ticks_diff(proximo_instante, ticks_us()) > 0:
                pass
    finally:
        gc.enable()

    dac.write(128)
    sleep_ms(100)

    print("Reproducción terminada.")

    mostrar(oled, [
        "PRUEBA TERMINADA",
        "",
        "REINICIANDO...",
        "LUEGO USE F5"
    ])

except KeyboardInterrupt:
    print()
    print("Prueba interrumpida.")

except OSError as error:
    print()
    print("Error de hardware:", error)

    if "-259" in str(error) or "ESP_ERR_INVALID_STATE" in str(error):
        print("El DAC quedó reservado por una ejecución anterior.")
        print("Se hará un reinicio físico para liberarlo.")

finally:
    if microfono is not None:
        try:
            microfono.deinit()
        except Exception:
            pass

    if dac is not None:
        try:
            dac.write(128)
        except Exception:
            pass

    mostrar(oled, [
        "REINICIO FISICO",
        "ESPERE...",
        "",
        "DESPUES USE F5"
    ])

    print("Reinicio físico en 2 segundos...")
    sleep_ms(2000)

    # Reinicio completo del microcontrolador: libera el DAC.
    machine.reset()
