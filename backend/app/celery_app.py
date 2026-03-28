from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "wallet",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.catalog_sync", "app.tasks.rate_sync"],
)

if not settings.DEV_MODE:
    celery_app.conf.beat_schedule = {
        "sync-fiat-catalog": {
            "task": "app.tasks.catalog_sync.sync_fiat_catalog",
            "schedule": crontab(hour=2, minute=0),
        },
        "sync-crypto-catalog": {
            "task": "app.tasks.catalog_sync.sync_crypto_catalog",
            "schedule": crontab(hour=2, minute=30),
        },
        "refresh-fiat-rates": {
            "task": "app.tasks.rate_sync.refresh_fiat_rates",
            "schedule": crontab(hour=17, minute=0),
        },
        "refresh-crypto-rates": {
            "task": "app.tasks.rate_sync.refresh_crypto_rates",
            "schedule": crontab(hour=18, minute=0),
        },
    }

celery_app.conf.task_routes = {
    "app.tasks.catalog_sync.*": {"queue": "catalog"},
    "app.tasks.rate_sync.*": {"queue": "rates"},
}

celery_app.conf.timezone = "UTC"
