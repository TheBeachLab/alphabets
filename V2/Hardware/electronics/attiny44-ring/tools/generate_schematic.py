#!/usr/bin/env python3
"""Generate the Alphabets V2 ATtiny44 ring schematic deterministically."""

from __future__ import annotations

import argparse
import copy
import uuid
from pathlib import Path

from kiutils.items.common import Effects, Font, Position, Property, Stroke, TitleBlock
from kiutils.items.schitems import (
    Connection,
    GlobalLabel,
    HierarchicalSheetInstance,
    NoConnect,
    SchematicSymbol,
    SymbolProjectInstance,
    SymbolProjectPath,
)
from kiutils.schematic import Schematic
from kiutils.symbol import SymbolLib


PROJECT = "attiny44-ring"
SCHEMATIC_UUID = "a28f3aa4-9690-4cb4-9ef8-8380353b4fb7"


COMPONENTS = [
    ("J1", "CONN6", "CHAIN_IN", (43.18, 55.88), {"1": "+5V", "2": "GND", "3": "CLOCK", "4": "LATCH", "5": "DATA_IN", "6": "RETURN"}),
    ("J2", "CONN6", "CHAIN_OUT", (43.18, 86.36), {"1": "+5V", "2": "GND", "3": "CLOCK", "4": "LATCH", "5": "DATA_OUT", "6": "RETURN"}),
    ("U1", "ATTINY44A", "ATtiny44A-SS", (127.0, 73.66), {"1": "+5V", "2": "PB0", "3": "PB1", "4": "RESET", "5": "HOME", "6": "LATCH", "7": "DATA_IN", "8": "DATA_OUT", "9": "CLOCK", "10": "MOTOR4", "11": "MOTOR3", "12": "MOTOR2", "13": "MOTOR1", "14": "GND"}),
    ("U2", "ULN2003A", "ULN2003A", (182.88, 73.66), {"1": "MOTOR1", "2": "MOTOR2", "3": "MOTOR3", "4": "MOTOR4", "8": "GND", "9": "+5V", "13": "COIL_D", "14": "COIL_C", "15": "COIL_B", "16": "COIL_A"}),
    ("J3", "CONN5", "28BYJ-48", (226.06, 58.42), {"1": "COIL_A", "2": "COIL_B", "3": "COIL_C", "4": "COIL_D", "5": "+5V"}),
    ("J4", "CONN3", "HOME_SENSOR", (223.52, 91.44), {"1": "+5V", "2": "GND", "3": "HOME"}),
    ("J5", "ISP6", "AVR_ISP_2X3", (175.26, 121.92), {"1": "DATA_OUT", "2": "+5V", "3": "CLOCK", "4": "DATA_IN", "5": "RESET", "6": "GND"}),
    ("J6", "CONN2", "5V_INJECT", (223.52, 121.92), {"1": "+5V", "2": "GND"}),
    ("R1", "R", "10k HOME pull-up", (88.9, 101.6), {"1": "+5V", "2": "HOME"}),
    ("R2", "R", "10k RESET pull-up", (111.76, 101.6), {"1": "+5V", "2": "RESET"}),
    ("C1", "C", "100n MCU", (127.0, 109.22), {"1": "+5V", "2": "GND"}),
    ("C2", "C", "100n DRIVER", (144.78, 109.22), {"1": "+5V", "2": "GND"}),
    ("C3", "C", "10n HOME filter", (157.48, 101.6), {"1": "HOME", "2": "GND"}),
    ("C4", "CP", "47u 10V", (193.04, 109.22), {"1": "+5V", "2": "GND"}),
    ("TP1", "TESTPOINT", "PB0", (76.2, 116.84), {"1": "PB0"}),
    ("TP2", "TESTPOINT", "PB1", (91.44, 116.84), {"1": "PB1"}),
]


NO_CONNECTS = {"U2": {"5", "6", "7", "10", "11", "12"}}
NO_BOM_REFS = {"TP1", "TP2"}


def uid(name: str) -> str:
    return str(uuid.uuid5(uuid.UUID(SCHEMATIC_UUID), name))


def all_pins(symbol):
    pins = list(symbol.pins)
    for unit in symbol.units:
        pins.extend(unit.pins)
    return {str(pin.number): pin for pin in pins}


def transform_pin(origin: tuple[float, float], pin) -> tuple[float, float]:
    return (round(origin[0] + pin.position.X, 4), round(origin[1] - pin.position.Y, 4))


def stub_endpoint(origin: tuple[float, float], pin_position: tuple[float, float]) -> tuple[float, float]:
    dx = pin_position[0] - origin[0]
    dy = pin_position[1] - origin[1]
    if dx != 0:
        return (round(pin_position[0] + (5.08 if dx > 0 else -5.08), 4), pin_position[1])
    return (pin_position[0], round(pin_position[1] + (5.08 if dy > 0 else -5.08), 4))


def make_property(key: str, value: str, x: float, y: float, *, hidden: bool = False) -> Property:
    return Property(
        key=key,
        value=value,
        position=Position(X=x, Y=y, angle=0),
        effects=Effects(font=Font(width=1.27, height=1.27), hide=hidden),
    )


def generate(symbol_path: Path, output_path: Path) -> None:
    library = SymbolLib.from_file(str(symbol_path))
    source_symbols = {symbol.libId: symbol for symbol in library.symbols}

    schematic = Schematic.create_new()
    schematic.version = "20231120"
    schematic.generator = "alphabets_v2_generator"
    schematic.uuid = SCHEMATIC_UUID
    schematic.titleBlock = TitleBlock(
        title="Alphabets V2 ATtiny44 SPI ring module",
        date="2026-08-15",
        revision="1.0",
        company="TheBeachLab / Alphabets",
        comments={
            1: "5 V module for 28BYJ-48 unipolar motor",
            2: "CLOCK + LATCH shared; DATA regenerated; RETURN passed through",
            3: "Ring connector order: +5V, GND, CLOCK, LATCH, DATA, RETURN",
            4: "Open-collector home input with pull-up and RC filter",
        },
    )
    schematic.sheetInstances = [HierarchicalSheetInstance(instancePath="/", page="1")]

    used_symbol_names = sorted({component[1] for component in COMPONENTS})
    for name in used_symbol_names:
        embedded = copy.deepcopy(source_symbols[name])
        embedded.libId = f"attiny44-ring:{name}"
        schematic.libSymbols.append(embedded)

    for ref, symbol_name, value, origin, net_by_pin in COMPONENTS:
        definition = source_symbols[symbol_name]
        pins = all_pins(definition)
        footprint = next((prop.value for prop in definition.properties if prop.key == "Footprint"), "")
        datasheet = next((prop.value for prop in definition.properties if prop.key == "Datasheet"), "")
        component_uuid = uid(f"component:{ref}")
        instance = SchematicSymbol(
            libraryNickname="attiny44-ring",
            entryName=symbol_name,
            position=Position(X=origin[0], Y=origin[1], angle=0),
            unit=1,
            inBom=ref not in NO_BOM_REFS,
            onBoard=True,
            dnp=False,
            fieldsAutoplaced=True,
            uuid=component_uuid,
            properties=[
                make_property("Reference", ref, origin[0], origin[1] - 22.86),
                make_property("Value", value, origin[0], origin[1] - 20.32),
                make_property("Footprint", footprint, origin[0], origin[1], hidden=True),
                make_property("Datasheet", datasheet, origin[0], origin[1], hidden=True),
                make_property("Description", "", origin[0], origin[1], hidden=True),
            ],
            pins={number: uid(f"pin:{ref}:{number}") for number in pins},
            instances=[
                SymbolProjectInstance(
                    name=PROJECT,
                    paths=[
                        SymbolProjectPath(
                            sheetInstancePath=f"/{SCHEMATIC_UUID}",
                            reference=ref,
                            unit=1,
                        )
                    ],
                )
            ],
        )
        schematic.schematicSymbols.append(instance)

        for number, net in net_by_pin.items():
            pin_position = transform_pin(origin, pins[number])
            endpoint = stub_endpoint(origin, pin_position)
            schematic.graphicalItems.append(
                Connection(
                    type="wire",
                    points=[Position(X=pin_position[0], Y=pin_position[1]), Position(X=endpoint[0], Y=endpoint[1])],
                    stroke=Stroke(width=0, type="default"),
                    uuid=uid(f"wire:{ref}:{number}"),
                )
            )
            schematic.globalLabels.append(
                GlobalLabel(
                    text=net,
                    shape="passive",
                    position=Position(X=endpoint[0], Y=endpoint[1], angle=0),
                    effects=Effects(font=Font(width=1.27, height=1.27)),
                    uuid=uid(f"label:{ref}:{number}"),
                )
            )

        for number in NO_CONNECTS.get(ref, set()):
            pin_position = transform_pin(origin, pins[number])
            schematic.noConnects.append(
                NoConnect(
                    position=Position(X=pin_position[0], Y=pin_position[1]),
                    uuid=uid(f"nc:{ref}:{number}"),
                )
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    schematic.to_file(str(output_path), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    generate(args.symbols, args.output)


if __name__ == "__main__":
    main()
