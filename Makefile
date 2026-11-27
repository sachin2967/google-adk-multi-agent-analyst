.PHONY: setup data test lint format benchmark api dashboard docker

PYTHON ?= python
CHECKED = src api tests data scripts streamlit_app

setup:
	$(PYTHON) -m pip install -r requirements-dev.txt

data:
	$(PYTHON) data/create_db.py

lint:
	$(PYTHON) -m ruff check $(CHECKED)
	$(PYTHON) -m ruff format --check $(CHECKED)

format:
	$(PYTHON) -m ruff format $(CHECKED)

test: lint
	$(PYTHON) -m pytest -q

benchmark:
	$(PYTHON) scripts/run_benchmark.py

api:
	$(PYTHON) -m uvicorn api.app:app --host 127.0.0.1 --port 8040 --workers 1

dashboard:
	ANALYST_API_URL=http://127.0.0.1:8040 $(PYTHON) -m streamlit run streamlit_app/app.py --server.address 127.0.0.1 --server.port 8540

docker:
	docker compose up --build
