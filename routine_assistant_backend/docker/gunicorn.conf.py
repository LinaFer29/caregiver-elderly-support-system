"""Gunicorn configuration shared by local and server deployments."""

import os
import time


workers = 1
worker_class = "gthread"
threads = 2
timeout = 180
preload_app = False

READY_FILE = "/tmp/model_warmup.ready"


def _elapsed_ms(started_at):
    return (time.perf_counter() - started_at) * 1000


def post_worker_init(worker):
    started_at = time.perf_counter()
    print("MODEL WARMUP start", flush=True)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "routine_assistant_backend.settings")

    import django

    django.setup()

    from voice.services.response_service import ResponseService
    from voice.services.whisper_service import WhisperService

    stage_started_at = time.perf_counter()
    print("MODEL WARMUP whisper start", flush=True)
    WhisperService.get_model()
    print(
        "MODEL WARMUP whisper ready elapsed_ms={:.3f}".format(
            _elapsed_ms(stage_started_at)
        ),
        flush=True,
    )

    stage_started_at = time.perf_counter()
    print("MODEL WARMUP semantic start", flush=True)
    ResponseService.get_semantic_model()
    ResponseService.get_semantic_catalog_cache()
    print(
        "MODEL WARMUP semantic ready elapsed_ms={:.3f}".format(
            _elapsed_ms(stage_started_at)
        ),
        flush=True,
    )

    with open(READY_FILE, "w", encoding="utf-8") as ready_file:
        ready_file.write("ready\n")

    print(
        "MODEL WARMUP complete elapsed_ms={:.3f}".format(
            _elapsed_ms(started_at)
        ),
        flush=True,
    )
