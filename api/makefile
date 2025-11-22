install:
	@ pip install uv
	@ uv sync --all-extras

install-updates:
	@ pip install uv
	@ uv sync --upgrade --refresh --all-extras

list-outdated: install
	@ pip list -o

lint-check:
	@ uv run lint-check --new *.py ./rangeseeker ./scripts

lint-check-ci:
	@ uv run lint-check --new *.py ./rangeseeker ./scripts --output-file lint-check-results.json --output-format annotations

lint-fix:
	@ uv run isort --sl -l 1000 *.py ./rangeseeker ./scripts
	@ uv run lint-check --new --fix *.py ./rangeseeker ./scripts

type-check:
	@ uv run type-check *.py ./rangeseeker ./scripts

type-check-ci:
	@ uv run type-check *.py ./rangeseeker ./scripts --output-file type-check-results.json --output-format annotations

security-check:
	@ uv run security-check *.py ./rangeseeker ./scripts

security-check-ci:
	@ uv run security-check *.py ./rangeseeker ./scripts --output-file security-check-results.json --output-format annotations

build:
	@ echo "Not Supported"

start:
	@ uv run uvicorn application:app --host 0.0.0.0 --port 5000 --no-access-log --reload

start-prod:
	@ uv run uvicorn application:app --host 0.0.0.0 --port 5000 --no-access-log

start-worker:
	@ uv run worker.py

start-worker-prod:
	@ uv run worker.py

test:
	@ echo "Not Supported"

clean:
	@ rm -rf ./.mypy_cache ./__pycache__ ./build ./dist

.PHONY: *
