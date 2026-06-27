from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery("research_worker", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_routes = {"app.workers.tasks.*": {"queue": "documents"}}
celery_app.conf.task_track_started = True
celery_app.conf.worker_prefetch_multiplier = 1
