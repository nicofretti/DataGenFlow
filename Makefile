.PHONY: check-deps install dev dev-ui dev-backend run-dev build-ui run mock-llm clean lint format lint-frontend format-frontend format-all lint-all typecheck typecheck-frontend typecheck-all test test-integration test-e2e test-e2e-ui pre-merge setup

# check if required dependencies are installed
check-deps:
	@echo "Checking dependencies..."
	@command -v uv >/dev/null 2>&1 || { \
		echo "❌ uv is not installed"; \
		echo ""; \
		echo "Please install uv:"; \
		echo " 	curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		echo ""; \
		echo "Or visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	}
	@command -v yarn >/dev/null 2>&1 || { \
		echo "❌ yarn is not installed"; \
		echo ""; \
		echo "Please install yarn:"; \
		echo " 	npm install -g yarn"; \
		echo ""; \
		echo "Or visit: https://yarnpkg.com/getting-started/install"; \
		exit 1; \
	}
	@echo "✅ All dependencies are installed"

install: check-deps
	uv venv && uv sync
	cd frontend && yarn install

dev: check-deps
	uv venv && uv sync --extra dev
	cd frontend && yarn install

dev-ui:
	cd frontend && yarn dev

dev-backend:
	uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000

run-dev:
	@echo "Starting backend and frontend in development mode..."
	@echo "Press Ctrl+C to stop both servers"
	@trap 'kill 0' SIGINT; \
	uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000 & \
	cd frontend && yarn dev & \
	wait

build-ui:
	cd frontend && yarn build

run: build-ui
	uv run python app.py --host 0.0.0.0

mock-llm:
	uv run python mock_llm.py

clean:
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf .mypy_cache .ruff_cache
	rm -rf *.pyc */*.pyc */*/*.pyc
	rm -rf data/*.db
	rm -rf frontend/build frontend/node_modules

lint:
	uv run ruff check .

format:
	uv run ruff format .

lint-frontend:
	cd frontend && yarn lint

format-frontend:
	cd frontend && yarn format

format-all: format format-frontend

lint-all: lint lint-frontend

typecheck:
	uv run mypy .

typecheck-frontend:
	cd frontend && yarn type-check

typecheck-all: typecheck typecheck-frontend

test:
	uv run pytest

test-integration:
	uv run pytest -m integration -v

test-e2e:
	./tests/e2e/run_all_tests.sh

test-e2e-ui:
	./tests/e2e/run_all_tests.sh --ui

pre-merge: format-all lint-all typecheck-all test 
	@echo "✅ Pre-merge checks completed successfully. Ready to merge!"

setup:
	cp .env.example .env
	mkdir -p data

all: dev setup format lint typecheck
