# Aura: Sistema de asistencia y monitoreo para cuidadores de adultos mayores basado en asistente de voz - Proyecto de Grado

Aura es un sistema para apoyar la gestión y seguimiento de rutinas de cuidado de adultos mayores. La aplicación permite que un cuidador administre adultos mayores, actividades, categorías, rutinas programadas y dispositivos ESP32 asociados para emitir recordatorios por voz y recibir respuestas habladas.

## Versión vigente

La rama `version-2` corresponde a la versión actual y funcional del proyecto. Este README documenta el estado implementado en esa rama y no toma como referencia `main`, `master` u otras ramas.

## Arquitectura general

El proyecto está organizado en cuatro bloques principales:

- `frontend/care-assistant-app/`: aplicación web para cuidadores desarrollada con React, TypeScript y Vite.
- `routine_assistant_backend/`: API REST y servicios de voz desarrollados con Django, Django REST Framework, Celery y SQLite.
- `ESP32/`: firmware y pruebas del dispositivo físico. La versión principal está en Arduino/C++ dentro de `ESP32/routine_assistant/`.
- `deployment/`: configuración de Mosquitto para el broker MQTT usado por Docker Compose.

En ejecución completa, el frontend consume la API del backend; el backend programa rutinas y asignaciones; Celery Beat revisa cada minuto las asignaciones pendientes; Celery Worker publica recordatorios por MQTT; el ESP32 recibe el mensaje, descarga el audio generado por el backend, lo reproduce por Bluetooth, graba la respuesta del usuario y la envía al backend para transcripción y actualización de estado.

## Tecnologías utilizadas

### Backend

- Python 3.11
- Django 5.2
- Django REST Framework
- Simple JWT para autenticación
- Celery con Redis como broker/result backend
- SQLite como base de datos configurada
- Mosquitto/MQTT mediante `paho-mqtt`
- Faster Whisper para STT en español
- Sentence Transformers para interpretación semántica de respuestas
- Edge TTS y `ffmpeg` para generación de audio WAV
- Gunicorn en despliegue Docker

### Frontend

- React 19
- TypeScript
- Vite
- React Router
- Axios
- Tailwind CSS
- React Hook Form y Zod
- Lucide React

### Dispositivo físico

- ESP32
- Firmware Arduino/C++
- Wi-Fi
- MQTT
- HTTP
- LittleFS
- Bluetooth A2DP para reproducción en parlante
- Micrófono I2S INMP441
- Sensor táctil TTP223B

También existen archivos MicroPython y diagnósticos en `ESP32/`, pero la implementación principal documentada es la de `ESP32/routine_assistant/`.

## Funcionalidades implementadas

- Registro e inicio de sesión de cuidadores con JWT.
- Consulta del usuario autenticado y renovación de token.
- Gestión de adultos mayores asociados a un cuidador.
- Gestión de categorías y actividades.
- Gestión de rutinas por adulto mayor, con actividades programadas por fecha, hora y frecuencia.
- Creación, edición, consulta y eliminación de rutinas desde el frontend.
- Catálogo de actividades para construir rutinas.
- Resumen diario de asignaciones por adulto mayor.
- Asociación de dispositivos físicos a adultos mayores mediante número de serie.
- Despacho automático de recordatorios pendientes con Celery Beat y Celery Worker.
- Publicación de recordatorios al ESP32 por MQTT.
- Generación de audio TTS para recordatorios.
- Descarga de audio desde el ESP32 vía HTTP.
- Captura de respuesta hablada en el ESP32 y envío al backend.
- Procesamiento STT con Faster Whisper.
- Interpretación de respuestas como `completed`, `missed` o `unknown`.
- Actualización de asignaciones con respuesta, hora de respuesta y estado cuando aplica.

## Flujo del sistema

1. El cuidador crea adultos mayores, categorías, actividades y rutinas desde el frontend.
2. El frontend usa `VITE_API_URL` para consumir la API REST del backend.
3. El backend crea registros `Program` y `Assignment` para las actividades programadas.
4. Celery Beat ejecuta cada minuto la tarea `voice.tasks.dispatch_due_assignments`.
5. La tarea busca asignaciones `pending` programadas para el minuto actual.
6. Para cada asignación con dispositivo asociado, el backend genera un mensaje TTS y publica un payload MQTT en el tópico `device/<mac-sin-dos-puntos>/audio`.
7. El ESP32 escucha su tópico, valida el payload, descarga el WAV desde `/assistant/audio/<archivo>/` y lo reproduce por Bluetooth.
8. Si el usuario toca el sensor, el ESP32 graba audio PCM16 mono a 16 kHz desde el micrófono I2S.
9. El ESP32 envía la grabación a `/assistant/stt/` con `mac_address`, `assignment_id` y `sample_rate`.
10. El backend normaliza el audio, transcribe con Faster Whisper, interpreta la respuesta y actualiza la asignación.

## API principal

Base local de la API:

```text
http://localhost:8000/api/v1/
```

Endpoints relevantes:

- `POST /register/`: registra un cuidador.
- `POST /login/`: obtiene tokens `access` y `refresh`.
- `POST /refresh/`: renueva el token de acceso.
- `GET /me/`: consulta el usuario autenticado.
- `GET/POST/PUT/PATCH/DELETE /caregivers/`: gestión de cuidadores del usuario autenticado.
- `GET/POST/PUT/PATCH/DELETE /elderly/`: gestión de adultos mayores del cuidador.
- `POST /devices/associate/`: asocia un dispositivo existente a un adulto mayor.
- `GET/POST/PUT/PATCH/DELETE /categories/`: gestión de categorías.
- `GET/POST/PUT/PATCH/DELETE /activities/`: gestión de actividades.
- `GET/POST/PUT/PATCH/DELETE /programs/`: gestión de programaciones.
- `GET/POST/PUT/PATCH/DELETE /assigments/`: gestión base de asignaciones.
- `GET/POST /routines/`: lista o crea rutinas por adulto mayor.
- `GET/PUT/DELETE /routines/<elderly_id|YYYY-MM-DD>/`: consulta, edita o elimina una rutina diaria.
- `GET /routines/catalog/`: lista actividades disponibles para armar rutinas.
- `GET /routines/daily-summary/`: devuelve resumen diario de asignaciones.
- `GET /activities-with-program/`: lista actividades con programación.
- `POST /activities-with-program/`: crea actividad, programación y asignación.
- `PUT /activities-with-program/<activity_id>/`: actualiza actividad y programación.

Endpoints de voz y dispositivo:

- `GET /api/voice/reminders?mac_address=<mac>`: consulta recordatorios vencidos para un dispositivo.
- `POST /assistant/stt/`: recibe audio de respuesta y procesa STT.
- `GET /assistant/audio/<file_name>/`: sirve audios WAV generados por TTS.

La documentación DRF está disponible en:

```text
http://localhost:8000/api/v1/docs/app/activities
```

## Requisitos

- Python 3.11+
- Node.js 20 recomendado para el frontend actual
- npm
- Docker y Docker Compose para ejecución integrada
- `ffmpeg` si se ejecuta el backend localmente sin Docker
- Redis si se ejecutan Celery Worker y Beat localmente sin Docker
- Broker MQTT Mosquitto si se prueba el ESP32 sin Docker Compose

## Variables de entorno

Existe un archivo de referencia en `.env.example`. No se deben versionar credenciales reales.

Para Docker Compose, crear `.env` en la raíz del proyecto con variables como:

```env
DJANGO_SECRET_KEY=replace-with-a-long-random-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,backend
DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:5173
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
MQTT_BROKER=mosquitto
MQTT_PORT=1883
MQTT_USER=replace-with-mqtt-user
MQTT_PASSWORD=replace-with-mqtt-password
MQTT_KEEPALIVE=60
FRONTEND_HOST_PORT=18080
VITE_API_URL=/api/v1
```

Para ejecución manual del backend, crear `routine_assistant_backend/.env`. Si Redis y MQTT corren en la máquina local, usar valores como `redis://localhost:6379/0`, `MQTT_BROKER=localhost` y el puerto MQTT disponible.

Para el frontend local, configurar `frontend/care-assistant-app/.env`:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

## Ejecución con Docker Compose

Desde la raíz del proyecto:

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

Servicios principales:

- Frontend/Nginx: `http://localhost:18080` si `FRONTEND_HOST_PORT=18080`.
- Backend Django: `http://localhost:8000` por el override local.
- MQTT Mosquitto para el ESP32: puerto host `1884`, redirigido al puerto `1883` del contenedor.
- Redis, Celery Worker y Celery Beat corren como servicios internos.

Comandos útiles:

```bash
docker compose logs backend
docker compose logs celery_worker
docker compose logs celery_beat
docker compose logs mosquitto
docker compose logs frontend
docker compose down
```

El primer arranque puede tardar mientras se descargan o preparan dependencias de voz y modelos.

## Ejecución local sin Docker

### Backend

```bash
cd routine_assistant_backend
python3 -m venv venv
source venv/bin/activate
pip install --index-url https://download.pytorch.org/whl/cpu torch==2.5.1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

El backend queda disponible en:

```text
http://localhost:8000
```

### Celery y Redis

En terminales separadas, con Redis activo:

```bash
cd routine_assistant_backend
source venv/bin/activate
celery -A routine_assistant_backend worker --loglevel=info
```

```bash
cd routine_assistant_backend
source venv/bin/activate
celery -A routine_assistant_backend beat --loglevel=info
```

### Frontend

```bash
cd frontend/care-assistant-app
npm install
npm run dev
```

El frontend de desarrollo queda disponible en:

```text
http://localhost:5173
```

## ESP32

La implementación principal del dispositivo está en `ESP32/routine_assistant/`.

Antes de cargar el firmware, configurar `ESP32/routine_assistant/config.h` con:

- Credenciales Wi-Fi.
- Host y puerto HTTP del backend.
- Host, puerto, usuario y contraseña MQTT.
- Nombre del parlante Bluetooth.
- Pines del sensor táctil y micrófono I2S si el hardware cambia.

Contrato actual del dispositivo:

- Tópico MQTT: `device/<mac-sin-dos-puntos-en-minusculas>/audio`.
- Payload MQTT esperado: JSON con `type`, `assignment_id`, `activity`, `message`, `scheduled_time` y `audio_file`.
- Audio de recordatorio: WAV servido desde `/assistant/audio/<file_name>/`.
- Respuesta de voz: PCM16 mono, little endian, 16 kHz, enviada a `/assistant/stt/`.
- Flujo físico: recibir recordatorio, reproducir por Bluetooth, esperar toque, grabar respuesta y enviar STT.

Para pruebas locales con Docker Compose, el firmware suele apuntar al IP de la máquina que ejecuta Docker, con backend en puerto `8000` y MQTT en puerto `1884`.

## Estructura del proyecto

```text
DesarrolloProyecto/
├── DatosPruebaJSON/
├── deployment/
│   └── mosquitto/
├── ESP32/
│   ├── routine_assistant/
│   ├── services/
│   ├── models/
│   └── diagnostics/
├── frontend/
│   └── care-assistant-app/
│       ├── src/
│       └── deployment/nginx/
├── routine_assistant_backend/
│   ├── activities/
│   ├── routines/
│   ├── users/
│   ├── voice/
│   ├── docker/
│   ├── routine_assistant_backend/
│   └── manage.py
├── docker-compose.yml
├── docker-compose.override.yml
└── .env.example
```

## Datos de prueba

La carpeta `DatosPruebaJSON/` contiene archivos JSON de referencia:

- `activities.json`
- `categories.json`
- `programs.json`
- `users.json`
- `caregivers.json`
- `elderly.json`

## Notas técnicas

- La API usa autenticación JWT mediante el encabezado `Authorization: Bearer <token>`.
- El backend carga variables desde `routine_assistant_backend/.env` en ejecución local.
- Docker Compose usa `.env` desde la raíz del repositorio.
- El backend almacena audios generados en `routine_assistant_backend/media/assistant_audio/`.
- La zona horaria configurada es `America/Bogota`.
- Las asignaciones pueden quedar `pending`, `completed` o `missed`.
- Si la respuesta de voz no se interpreta con suficiente confianza, el resultado queda como `unknown` y la asignación no cambia de estado.
