# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
PYTHON ?= .venv/bin/python
UV ?= uv
CQ_EDITOR ?= cq-editor
PROFILE ?= ../../Final/design.toml
OUTPUT ?= ../../Final/generated/mechanical
VARIANT ?= definitive
OCP_ENV ?= .ocp-venv

.PHONY: setup setup-vscode gui gui-enclosure generate generate-captured-enclosure lint test check verify-generated clean-generated

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

generate-captured-enclosure:
	PYTHONPATH=. $(PYTHON) export_captured_enclosure.py --variant $(VARIANT) --output ../../Final/generated/enclosure $(if $(PROFILE),--profile $(PROFILE))

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

test:
	PYTHONPATH=. $(PYTHON) -m pytest -q

check: generate generate-captured-enclosure lint test

verify-generated: check
	git diff --exit-code -- generated

clean-generated:
	rm -rf ../../Final/generated/mechanical ../../Final/generated/enclosure
