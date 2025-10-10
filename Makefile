.PHONY: check-deps install dev dev-ui build-ui run mock-llm generate list export clean lint format lint-frontend format-frontend format-all lint-all typecheck typecheck-frontend typecheck-all test setup

# check if required dependencies are installed
check-deps:
	@echo "Checking dependencies..."
	@command -v uv >/dev/null 2>&1 || { \
		echo "❌ uv is not installed"; \
		echo ""; \
		echo "Please install uv:"; \
		echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		echo ""; \
		echo "Or visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	}
	@command -v yarn >/dev/null 2>&1 || { \
		echo "❌ yarn is not installed"; \
		echo ""; \
		echo "Please install yarn:"; \
		echo "  npm install -g yarn"; \
		echo ""; \
		echo "Or visit: https://yarnpkg.com/getting-started/install"; \
		exit 1; \
	}
	@echo "✅ All dependencies are installed"

install: check-deps
	uv pip install -e .
	cd frontend && yarn install

dev: check-deps
	uv pip install -e ".[dev]"
	cd frontend && yarn install

dev-ui:
	cd frontend && yarn dev

build-ui:
	cd frontend && yarn build

run: build-ui
	python3 app.py

mock-llm:
	python3 mock_llm.py

generate:
	python3 cli.py generate $(FILE)

list:
	python3 cli.py list

export:
	python3 cli.py export $(OUTPUT)

clean:
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf .mypy_cache .ruff_cache
	rm -rf *.pyc */*.pyc */*/*.pyc
	rm -rf data/*.db
	rm -rf frontend/build frontend/.svelte-kit frontend/node_modules

lint:
	ruff check .

format:
	ruff format .

lint-frontend:
	cd frontend && yarn lint

format-frontend:
	cd frontend && yarn format

format-all: format format-frontend

lint-all: lint lint-frontend

typecheck:
	mypy .

typecheck-frontend:
	cd frontend && yarn type-check

typecheck-all: typecheck typecheck-frontend

test:
	pytest

setup:
	cp .env.example .env
	mkdir -p data

all: dev setup format lint typecheck
