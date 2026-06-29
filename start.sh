#!/bin/sh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
exec python -m gunicorn --chdir "$DIR/loanapproval" loanapproval.wsgi:application --bind 0.0.0.0:$PORT
