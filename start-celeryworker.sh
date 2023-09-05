#!/bin/bash

set -o errexit
set -o nounset

celery -A cpa worker -l INFO