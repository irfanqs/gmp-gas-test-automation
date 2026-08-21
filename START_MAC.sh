#!/bin/zsh
set -e
cd "$(dirname "$0")"
if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -r requirements.txt
open "http://127.0.0.1:5001"
exec .venv/bin/python app.py
