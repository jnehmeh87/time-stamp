#!/bin/sh
sleep 60
gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 300 time_stamp.wsgi:application