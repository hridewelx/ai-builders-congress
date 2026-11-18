# Lotline developer shortcuts. On Windows, run the commands from Git Bash.
PY ?= python3
PORT ?= 8077
HOST ?= 127.0.0.1

.PHONY: help install data verify seed reset run test lint

help:
	@echo "make install   install Python dependencies"
	@echo "make data      build the staged dataset (data/dataset/v1)"
	@echo "make verify    re-check every dataset hash"
	@echo "make seed      create the demo database (first run trains the model)"
	@echo "make reset     rebuild the demo database from scratch"
	@echo "make run       serve on http://$(HOST):$(PORT)"
	@echo "make test      run the test suite"
	@echo "make lint      run ruff over app, scripts and tests"

install:
	$(PY) -m pip install -r requirements.txt ruff

data:
	$(PY) scripts/build_dataset.py

verify:
	$(PY) scripts/build_dataset.py --verify

seed:
	$(PY) -m app.seed

reset:
	$(PY) -m app.seed --force

run:
	LOTLINE_DEMO=1 $(PY) -m uvicorn app.main:app --host $(HOST) --port $(PORT)

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check app scripts tests
