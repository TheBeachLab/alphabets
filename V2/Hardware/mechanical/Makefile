PYTHON ?= .venv/bin/python
UV ?= uv
CQ_EDITOR ?= cq-editor

.PHONY: setup gui generate lint test check verify-generated clean-generated

setup:
	$(UV) venv --python 3.12 .venv
	$(UV) pip install --python .venv/bin/python -r requirements.txt

gui:
	$(CQ_EDITOR) view.py

generate:
	PYTHONPATH=. $(PYTHON) generate.py

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

test:
	PYTHONPATH=. $(PYTHON) -m pytest -q

check: generate lint test

verify-generated: check
	git diff --exit-code -- generated

clean-generated:
	rm -rf generated
