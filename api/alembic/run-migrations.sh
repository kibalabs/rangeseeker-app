#!/usr/bin/env bash
set -e -o pipefail

echo "Running migrations..."
alembic --raiseerr upgrade head
echo "Completed migrations"
