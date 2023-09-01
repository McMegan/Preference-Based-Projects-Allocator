export LANG=C.UTF-8

gunicorn — bind=0.0.0.0 — timeout 600 config.wsgi & celery -A config worker -l INFO -B