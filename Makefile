.PHONY: install dev dev-ui build-ui run mock-llm generate list export clean lint format typecheck test setup

install:
	uv pip install -e .
	cd frontend && yarn install

dev:
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

typecheck:
	mypy .

test:
	pytest

setup:
	cp .env.example .env
	mkdir -p data

all: dev setup format lint typecheck
