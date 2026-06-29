#!/bin/sh
cd loanapproval
exec gunicorn loanapproval.wsgi:application --bind 0.0.0.0:$PORT
