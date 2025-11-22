install:
	@ pip install uv
	@ uv sync --all-extras

install-updates:
	@ pip install uv
	@ uv sync --upgrade --refresh --all-extras

list-outdated: install
	@ pip list -o

lint-check:
	@ uv run lint-check --new *.py ./rangeseeker

lint-check-ci:
	@ uv run lint-check --new *.py ./rangeseeker --output-file lint-check-results.json --output-format annotations

lint-fix:
	@ uv run isort --sl -l 1000 *.py ./rangeseeker
	@ uv run lint-check --new --fix *.py ./rangeseeker

type-check:
	@ uv run type-check *.py ./rangeseeker

type-check-ci:
	@ uv run type-check *.py ./rangeseeker --output-file type-check-results.json --output-format annotations

security-check:
	@ uv run security-check *.py ./rangeseeker

security-check-ci:
	@ uv run security-check *.py ./rangeseeker --output-file security-check-results.json --output-format annotations

build:
	@ echo "Not Supported"

start:
	@ uv run uvicorn application:app --host 0.0.0.0 --port 5000 --no-access-log --reload

start-prod:
	@ uv run uvicorn application:app --host 0.0.0.0 --port 5000 --no-access-log

test:
	@ echo "Not Supported"

clean:
	@ rm -rf ./.mypy_cache ./__pycache__ ./build ./dist

.PHONY: *
