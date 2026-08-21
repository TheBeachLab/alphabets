PYTHON ?= .venv/bin/python
UV ?= uv
CQ_EDITOR ?= cq-editor
PROFILE ?=
OUTPUT ?= generated
VARIANT ?= definitive
OCP_ENV ?= .ocp-venv

.PHONY: setup setup-vscode gui gui-enclosure generate lint test check verify-generated clean-generated

setup:
	$(UV) venv --python 3.12 .venv
	$(UV) pip install --python .venv/bin/python -r requirements.txt

setup-vscode:
	$(UV) venv --python 3.12 $(OCP_ENV)
	$(UV) pip install --python $(OCP_ENV)/bin/python -r requirements.txt -r requirements-vscode.txt

gui:
	ALPHABETS_PROFILE="$(PROFILE)" $(CQ_EDITOR) view.py

gui-enclosure:
	ALPHABETS_PROFILE="$(PROFILE)" $(CQ_EDITOR) view_enclosure.py

generate:
	PYTHONPATH=. $(PYTHON) generate.py --output $(OUTPUT) --variant $(VARIANT) $(if $(PROFILE),--profile $(PROFILE))

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
