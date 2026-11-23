#!/bin/sh
# SNAKE: REWIRED - Linux launcher.
# Creates a private .venv on first run (no manual setup needed), then starts
# the game. Requires: python3, python3-venv (and pip). No internet needed
# after the first install.
set -e
cd "$(dirname "$0")"
PY=python3
if ! $PY -c "import pygame" 2>/dev/null; then
  if [ ! -d .venv ]; then
    echo "First run: setting up a private Python environment..."
    $PY -m venv .venv
    ./.venv/bin/pip install --quiet --upgrade pip
    ./.venv/bin/pip install --quiet -r requirements.txt
  fi
  PY=./.venv/bin/python
fi
exec $PY main.py "$@"
