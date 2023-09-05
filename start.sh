#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

python manage.py migrate

gunicorn cpa.wsgi:application --bind 0.0.0.0:8080 --timeout 600 --preload --threads 2 -w 2 --log-level 'debug'