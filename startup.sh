export LANG=C.UTF-8

celery --app=cpa worker -l INFO & gunicorn --bind=0.0.0.0 --timeout 600 config.wsgi