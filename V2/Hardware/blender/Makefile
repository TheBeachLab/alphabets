# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT

PYTHON ?= ../mechanical/.venv/bin/python
BLENDER ?= /Applications/Blender.app/Contents/MacOS/Blender
UV ?= uv
FINAL_OUTPUT := ../../Final/generated/blender

.PHONY: setup assets scene interactive long-run hello-wall hello-wall-assets capture-envelope check check-steps open clean

setup:
	$(UV) pip install --python $(PYTHON) -r requirements.txt

assets:
	$(PYTHON) generate_assets.py --variant definitive --profile ../../Final/design.toml --output $(FINAL_OUTPUT)

scene: assets
	$(BLENDER) --background --python build_scene.py -- --assets-dir $(FINAL_OUTPUT) --output $(FINAL_OUTPUT)/alphabets-v2-gravity.blend --preview $(FINAL_OUTPUT)/alphabets-v2-gravity.png

interactive: assets
	$(BLENDER) --background --python build_scene.py -- --assets-dir $(FINAL_OUTPUT) --no-simulate --output $(FINAL_OUTPUT)/alphabets-v2-interactive.blend --preview $(FINAL_OUTPUT)/alphabets-v2-interactive.png

long-run: assets
	$(BLENDER) --background --python build_scene.py -- --assets-dir $(FINAL_OUTPUT) --no-simulate --long-run --output $(FINAL_OUTPUT)/alphabets-v2-long-run.blend --preview $(FINAL_OUTPUT)/alphabets-v2-long-run.png

hello-wall-assets:
	$(PYTHON) generate_hello_wall_assets.py

hello-wall: hello-wall-assets
	$(BLENDER) --background --python build_hello_wall.py -- --output $(FINAL_OUTPUT)/hello-wall/alphabets-hallo-welt-5x2.blend
	$(BLENDER) $(FINAL_OUTPUT)/hello-wall/alphabets-hallo-welt-5x2.blend --background --python validate_hello_wall.py

capture-envelope:
	$(BLENDER) $(FINAL_OUTPUT)/alphabets-v2-interactive.blend --background --python capture_card_envelope.py

check:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m pytest -q test_generate_assets.py test_hello_wall.py

check-steps: interactive
	$(BLENDER) $(FINAL_OUTPUT)/alphabets-v2-interactive.blend --background --python validate_appended_steps.py -- --steps 20
	$(BLENDER) $(FINAL_OUTPUT)/alphabets-v2-interactive.blend --background --python validate_appended_steps.py -- --steps 20 --single
	$(BLENDER) $(FINAL_OUTPUT)/alphabets-v2-interactive.blend --background --python validate_appended_steps.py -- --steps 2 --stale-scene-end 1088

open: interactive
	open -a Blender $(FINAL_OUTPUT)/alphabets-v2-interactive.blend

clean:
	rm -rf $(FINAL_OUTPUT)
