#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
uv run alembic upgrade head
