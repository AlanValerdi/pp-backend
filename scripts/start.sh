#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
./scripts/prestart.sh
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
