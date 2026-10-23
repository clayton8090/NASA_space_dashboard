PY := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: help setup key test run dashboard

help:
	@echo "make setup      create .venv and install dependencies"
	@echo "make key        store your NASA API key in the system keychain"
	@echo "make test       run the test suite"
	@echo "make run        fetch, clean and load fresh data into data/local.db"
	@echo "make dashboard  open the dashboard in your browser"

setup:
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

key:
	$(PY) scripts/store_key.py

test:
	$(PY) -m pytest -q

run:
	$(PY) -m src.pipeline

dashboard:
	.venv/bin/streamlit run app.py
