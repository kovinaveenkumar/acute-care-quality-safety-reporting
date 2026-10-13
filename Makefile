PY ?= .venv/bin/python
export PYTHONPATH := src

.PHONY: all data db reports app test docs clean
all: data db reports app docs test

data:    ## generate synthetic raw CSVs (seeded, reproducible)
	$(PY) -m qsr.generate_data
db:      ## clean raw data, log every fix, build SQLite + measure views
	$(PY) -m qsr.staging
reports: ## dashboard.html, Excel committee pack, PDF brief
	$(PY) -m qsr.build_reports
app:     ## export app/data.js for the QualityLens web app (open app/index.html)
	$(PY) -m qsr.export_app_data
docs:    ## regenerate the data dictionary from the live schema
	$(PY) -m qsr.make_docs
test:
	$(PY) -m pytest -q
clean:
	rm -rf data/quality.db data/raw/*.csv outputs/*
