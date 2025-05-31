#!/bin/bash
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python3 build.py

if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi 