#!/usr/bin/env bash

source env/bin/activate

# Starting the application hosted in a gunicorn server with 1 worker and 2 threads
gunicorn --workers=1 --threads=2 --bind :5000 wsgi:app