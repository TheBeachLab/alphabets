PYTHON ?= ../mechanical/.venv/bin/python
BLENDER ?= /Applications/Blender.app/Contents/MacOS/Blender
UV ?= uv

.PHONY: setup assets scene interactive long-run hello-wall hello-wall-assets check open clean

setup:
	$(UV) pip install --python $(PYTHON) -r requirements.txt

assets:
	$(PYTHON) generate_assets.py

scene: assets
	$(BLENDER) --background --python build_scene.py -- --output generated/alphabets-v2-gravity.blend --preview generated/alphabets-v2-gravity.png

interactive: assets
	$(BLENDER) --background --python build_scene.py -- --no-simulate --output generated/alphabets-v2-interactive.blend --preview generated/alphabets-v2-interactive.png

long-run: assets
	$(BLENDER) --background --python build_scene.py -- --no-simulate --long-run --output generated/alphabets-v2-long-run.blend --preview generated/alphabets-v2-long-run.png

hello-wall-assets:
	$(PYTHON) generate_hello_wall_assets.py

hello-wall: hello-wall-assets
	$(BLENDER) --background --python build_hello_wall.py -- --output generated/hello-wall/alphabets-hallo-welt-5x2.blend --preview generated/hello-wall/alphabets-hallo-welt-5x2.png
	$(BLENDER) generated/hello-wall/alphabets-hallo-welt-5x2.blend --background --python validate_hello_wall.py

check:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m pytest -q test_generate_assets.py test_hello_wall.py

open: interactive
	open -a Blender generated/alphabets-v2-interactive.blend

clean:
	rm -rf generated
