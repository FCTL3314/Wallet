# NOTE: All tasks use asyncio.run() to bridge sync Celery workers with async SQLAlchemy.
# This requires the default 'prefork' pool. Do NOT switch to 'gevent' or 'eventlet'.
# NullPool is used in _engine.py to avoid connection sharing after fork().
