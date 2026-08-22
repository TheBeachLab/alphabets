# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
PROJECT := attiny44-ring
KICAD_CLI ?= kicad-cli
KICAD_PYTHON ?= python3
KIUTILS_PYTHON ?= python3
FREEROUTING_JAR ?=
KICAD10_FOOTPRINT_DIR ?=

export KICAD10_FOOTPRINT_DIR

.PHONY: schematic board route organic autoroute check fabrication previews

schematic:
	$(KIUTILS_PYTHON) tools/generate_schematic.py --symbols $(PROJECT).kicad_sym --output $(PROJECT).kicad_sch
	$(KICAD_CLI) sch upgrade $(PROJECT).kicad_sch

board:
	$(KICAD_PYTHON) tools/generate_board.py --output $(PROJECT).kicad_pcb --dsn routing/$(PROJECT).dsn --footprints "$(KICAD10_FOOTPRINT_DIR)"

route:
	$(KICAD_PYTHON) tools/import_routing.py --board $(PROJECT).kicad_pcb --session routing/$(PROJECT).ses

organic:
	$(KICAD_PYTHON) tools/organicize_board.py --board $(PROJECT).kicad_pcb --kicad-cli "$(KICAD_CLI)"

autoroute:
	@test -n "$(FREEROUTING_JAR)" || (echo "FREEROUTING_JAR is required" >&2; exit 2)
	$(KICAD_PYTHON) tools/prepare_single_layer_dsn.py --input routing/$(PROJECT).dsn --output routing/$(PROJECT)-single-layer.dsn
	java -jar "$(FREEROUTING_JAR)" -de routing/$(PROJECT)-single-layer.dsn -do routing/$(PROJECT).ses -mp 300 -mt 4 -da --gui.enabled=false --api_server.enabled=false --logging.file.enabled=false
	$(MAKE) route

check:
	mkdir -p validation
	$(KICAD_PYTHON) tools/check_design.py --board $(PROJECT).kicad_pcb
	$(KICAD_CLI) sch erc --output validation/erc.rpt --exit-code-violations $(PROJECT).kicad_sch
	$(KICAD_CLI) pcb drc --output validation/drc-parity.rpt --schematic-parity --exit-code-violations $(PROJECT).kicad_pcb

fabrication:
	mkdir -p fabrication/gerbers
	$(KICAD_CLI) pcb export stats --output board-stats.json --format json --units mm $(PROJECT).kicad_pcb
	$(KICAD_PYTHON) ../../../Code/json_license_metadata.py board-stats.json
	$(KICAD_CLI) pcb export gerbers --output fabrication/gerbers --layers F.Cu,F.Mask,F.Silkscreen,Edge.Cuts $(PROJECT).kicad_pcb
	$(KICAD_CLI) pcb export drill --output fabrication/gerbers --format excellon --excellon-units mm --excellon-separate-th --generate-map --map-format svg --generate-report --report-path fabrication/drill-report.txt $(PROJECT).kicad_pcb
	$(KICAD_CLI) pcb export pos --output fabrication/$(PROJECT)-positions.csv --side front --format csv --units mm $(PROJECT).kicad_pcb
	$(KICAD_CLI) sch export bom --output fabrication/$(PROJECT)-bom.csv --fields Reference,Value,Footprint,QUANTITY --labels Refs,Value,Footprint,Qty --group-by Value,Footprint $(PROJECT).kicad_sch
	$(KICAD_CLI) pcb export step --force --output fabrication/$(PROJECT).step $(PROJECT).kicad_pcb

previews:
	mkdir -p preview
	$(KICAD_CLI) pcb render --output preview/top.png --side top --quality high --width 1400 --height 1500 --background opaque $(PROJECT).kicad_pcb
	$(KICAD_CLI) pcb export svg --output preview/copper.svg --mode-single --layers F.Cu,F.Silkscreen,Edge.Cuts --page-size-mode 2 --fit-page-to-board --exclude-drawing-sheet $(PROJECT).kicad_pcb
	$(KICAD_CLI) sch export svg --output preview --exclude-drawing-sheet $(PROJECT).kicad_sch
