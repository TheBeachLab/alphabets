PYTHON ?= ../mechanical/.venv/bin/python
BLENDER ?= /Applications/Blender.app/Contents/MacOS/Blender
UV ?= uv

.PHONY: setup assets scene interactive check open clean

setup:
	$(UV) pip install --python $(PYTHON) -r requirements.txt

assets:
	$(PYTHON) generate_assets.py

scene: assets
	$(BLENDER) --background --python build_scene.py -- --output generated/alphabets-v2-gravity.blend --preview generated/alphabets-v2-gravity.png

interactive: assets
	$(BLENDER) --background --python build_scene.py -- --no-simulate --output generated/alphabets-v2-interactive.blend --preview generated/alphabets-v2-interactive.png

check:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m pytest -q test_generate_assets.py

open: interactive
	open -a Blender generated/alphabets-v2-interactive.blend

clean:
	rm -rf generated
