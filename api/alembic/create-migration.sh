#!/usr/bin/env bash
set -e -o pipefail

message=$1

if [ -z "$1" ]; then
    echo "Error: message required as the first parameter"
    exit 1
fi

alembic revision --autogenerate -m "$1"
