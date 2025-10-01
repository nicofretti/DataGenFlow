.PHONY: install dev run mock-llm clean lint format typecheck test setup

install:
	uv pip install -e .

dev:
	uv pip install -e ".[dev]"

run:
	python3 app.py

mock-llm:
	python3 mock_llm.py

clean:
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf .mypy_cache .ruff_cache
	rm -rf *.pyc */*.pyc */*/*.pyc
	rm -rf data/*.db

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
