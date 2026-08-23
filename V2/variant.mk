# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT

REPO_ROOT := $(abspath ../..)
V2_DIR := $(abspath ..)
PYTHON ?= $(V2_DIR)/Hardware/mechanical/.venv/bin/python
BLENDER ?= /Applications/Blender.app/Contents/MacOS/Blender
FREECADCMD ?= /Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd
PROFILE := $(CURDIR)/design.toml
OUTPUT := $(CURDIR)/generated
CARDS := $(OUTPUT)/cards
STICKERS := $(OUTPUT)/stickers
MECHANICAL := $(OUTPUT)/mechanical
BLENDER_OUTPUT := $(OUTPUT)/blender
ENCLOSURE := $(OUTPUT)/enclosure
CARD_STEM := card-$(CARD_SIZE)
BLEND_FILE := $(BLENDER_OUTPUT)/alphabets-v2-$(FOLDER_SLUG).blend

.PHONY: all setup cards stickers mechanical blender enclosure check

all: cards stickers mechanical blender enclosure

setup:
	$(MAKE) -C $(V2_DIR)/Hardware/mechanical setup

cards:
	$(FREECADCMD) $(V2_DIR)/Hardware/cards/generate_card.py --pass '--variant $(VARIANT) --output-dir $(CARDS) --stem $(CARD_STEM)'

stickers:
	$(PYTHON) $(V2_DIR)/Hardware/stickers/generate_stickers.py --variant $(VARIANT) --color-preset black-white --output-svg $(STICKERS)/$(CHARACTER_PRESET)-black-white-$(STICKER_SIZE).svg --output-pdf $(STICKERS)/$(CHARACTER_PRESET)-black-white-$(STICKER_SIZE).pdf
	$(PYTHON) $(V2_DIR)/Hardware/stickers/generate_stickers.py --variant $(VARIANT) --color-preset black-yellow --output-svg $(STICKERS)/$(CHARACTER_PRESET)-black-yellow-$(STICKER_SIZE).svg --output-pdf $(STICKERS)/$(CHARACTER_PRESET)-black-yellow-$(STICKER_SIZE).pdf
	$(PYTHON) $(V2_DIR)/Hardware/stickers/generate_stickers.py --variant $(VARIANT) --color-preset yellow-black --output-svg $(STICKERS)/$(CHARACTER_PRESET)-yellow-black-$(STICKER_SIZE).svg --output-pdf $(STICKERS)/$(CHARACTER_PRESET)-yellow-black-$(STICKER_SIZE).pdf
	$(PYTHON) $(V2_DIR)/Hardware/stickers/generate_stickers.py --variant $(VARIANT) --color-preset white-black --output-svg $(STICKERS)/$(CHARACTER_PRESET)-white-black-$(STICKER_SIZE).svg --output-pdf $(STICKERS)/$(CHARACTER_PRESET)-white-black-$(STICKER_SIZE).pdf

mechanical:
	PYTHONPATH=$(V2_DIR)/Hardware/mechanical $(PYTHON) $(V2_DIR)/Hardware/mechanical/generate.py --variant $(VARIANT) --profile $(PROFILE) --output $(MECHANICAL)

blender: mechanical
	$(PYTHON) $(V2_DIR)/Hardware/blender/generate_assets.py --variant $(VARIANT) --profile $(PROFILE) --output $(BLENDER_OUTPUT)
	$(BLENDER) --background --python $(V2_DIR)/Hardware/blender/build_scene.py -- --assets-dir $(BLENDER_OUTPUT) --output $(BLEND_FILE) --preview $(BLENDER_OUTPUT)/alphabets-v2-$(FOLDER_SLUG).png
	$(BLENDER) $(BLEND_FILE) --background --python $(V2_DIR)/Hardware/blender/capture_cards.py -- --json-output $(BLENDER_OUTPUT)/cards-position-capture.json --blend-output $(BLEND_FILE)
	$(if $(REFERENCE_CAPTURE),$(PYTHON) $(V2_DIR)/Hardware/blender/retarget_card_capture.py --source-capture $(REFERENCE_CAPTURE) --source-scene $(REFERENCE_SCENE) --target-capture $(BLENDER_OUTPUT)/cards-position-capture.json --target-scene $(BLENDER_OUTPUT)/scene.json)

enclosure: blender
	PYTHONPATH=$(V2_DIR)/Hardware/mechanical $(PYTHON) $(V2_DIR)/Hardware/mechanical/export_captured_enclosure.py --variant $(VARIANT) --profile $(PROFILE) --capture $(BLENDER_OUTPUT)/cards-position-capture.json --output $(ENCLOSURE)

check:
	$(PYTHON) $(V2_DIR)/check_variant_package.py --variant $(VARIANT) --root $(CURDIR)
