export LANG=C.UTF-8

pip install -r requirements.txt && celery --app=cpa worker -l INFO