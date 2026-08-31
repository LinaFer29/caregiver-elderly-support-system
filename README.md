# Routine Assistant - Proyecto de Grado

Aplicación web para la gestión de rutinas y actividades de cuidado de adultos mayores.

El sistema está enfocado en cuidadores, quienes pueden:
- Registrarse e iniciar sesión.
- Crear y administrar categorías de actividades.
- Crear actividades con programación (fecha, hora, frecuencia, estado activo).
- Registrar y editar perfiles de adultos mayores asociados.
- Consultar actividades programadas.

## Arquitectura del Proyecto

El repositorio está organizado en 3 bloques principales:

- `routine_assistant_backend/`: API REST en Django + Django REST Framework.
- `frontend/care-assistant-app/`: aplicación web en React + TypeScript + Vite.
- `DatosPruebaJSON/`: archivos JSON con datos de prueba.

## Stack Tecnológico

### Backend
- Python 3.11
- Django 5.x
- Django REST Framework
- Simple JWT (`djangorestframework-simplejwt`)
- `django-cors-headers`
- SQLite (por defecto)

### Frontend
- React 19
- TypeScript
- Vite
- React Router
- Axios
- Tailwind CSS
- React Hook Form + Zod

## Modelo Funcional (Resumen)

### Usuarios
- `User` (custom): extiende `AbstractUser` con rol (`caregiver` o `elderly`).
- `Caregiver`: perfil de cuidador asociado 1:1 con `User`.
- `Elderly`: adulto mayor asociado a un `Caregiver`.

### Actividades
- `Category`: categoría personalizada por cuidador (nombre, color, icono).
- `Activity`: actividad (título, descripción, categoría).

### Rutinas
- `Program`: programación de una actividad (fecha, hora, frecuencia, activa/inactiva).
- `Assignment`: asignaciones de actividades a adultos mayores (modelo existente en backend).

## API REST (base)

Base URL backend local:
- `http://localhost:8000/api/v1/`

Endpoints principales:

### Autenticación y usuarios
- `POST /register/` registro de cuidador.
- `POST /login/` obtiene `access` y `refresh` JWT.
- `POST /refresh/` renueva token `access`.
- CRUD `GET/POST/PUT/DELETE /caregivers/`
- CRUD `GET/POST/PUT/DELETE /elderly/`

### Actividades y categorías
- CRUD `GET/POST/PUT/DELETE /activities/`
- CRUD `GET/POST/PUT/DELETE /categories/`

### Programación
- CRUD `GET/POST/PUT/DELETE /programs/`
- CRUD `GET/POST/PUT/DELETE /assigments/`
- `GET /activities-with-program/` lista actividades con su programación.
- `POST /activities-with-program/` crea actividad + programación en una sola operación.
- `PUT /activities-with-program/<activity_id>/` actualiza actividad + programación.

Documentación DRF habilitada en:
- `/api/v1/docs/app/activities`

## Requisitos Previos

- Python 3.11+
- Node.js 18+
- npm 9+

## Configuración y Ejecución

### 1) Backend

Desde la raíz del proyecto:

```bash
cd routine_assistant_backend
python3 -m venv venv
source venv/bin/activate
pip install django djangorestframework djangorestframework-simplejwt django-cors-headers coreapi paho-mqtt "celery[redis]" sentence-transformers
python manage.py migrate
python manage.py runserver
```

Backend por defecto en:
- `http://localhost:8000`

Para automatizar el envío de actividades pendientes por MQTT:

```bash
redis-server
cd routine_assistant_backend
celery -A routine_assistant_backend worker --loglevel=info
celery -A routine_assistant_backend beat --loglevel=info
```

### 2) Frontend

En otra terminal, desde la raíz:

```bash
cd frontend/care-assistant-app
npm install
npm run dev
```

Frontend por defecto en:
- `http://localhost:5173`

## Variables de Entorno

Archivo frontend:
- `frontend/care-assistant-app/.env`

Valor esperado:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

## Flujo de Uso Recomendado

1. Crear cuenta de cuidador (`/signup`).
2. Iniciar sesión (`/login`).
3. Crear categorías.
4. Crear actividad y programarla.
5. Registrar adultos mayores asociados.
6. Consultar, editar o desactivar actividades según necesidad.

## Datos de Prueba

La carpeta `DatosPruebaJSON/` contiene archivos de referencia:
- `activities.json`
- `categories.json`
- `programs.json`
- `users.json`
- `caregivers.json`
- `elderly.json`

## Notas Técnicas

- La API usa autenticación JWT en encabezado `Authorization: Bearer <token>`.
- El backend filtra datos por usuario autenticado en módulos clave (actividades, categorías, programas, adultos mayores).
- Existe una base local `db.sqlite3` incluida en el backend para desarrollo.
- Proyecto orientado a entorno de desarrollo (por ejemplo, `DEBUG=True` en configuración actual).

## Estructura de Carpetas

```text
DesarrolloProyecto/
├── DatosPruebaJSON/
├── frontend/
│   └── care-assistant-app/
└── routine_assistant_backend/
    ├── activities/
    ├── routines/
    ├── users/
    ├── routine_assistant_backend/
    └── manage.py
```
