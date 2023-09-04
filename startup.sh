export LANG=C.UTF-8

pipenv install && gunicorn --bind=0.0.0.0 --timeout 600 cpa.wsgi && celery --app=cpa worker -l INFO