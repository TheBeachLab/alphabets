#!/usr/bin/env python3
"""Generate the millable Alphabets V2 ATtiny1624 ring schematic."""

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


PROJECT = "attiny1624-ring"
SCHEMATIC_UUID = "3f45baf4-f217-4a9d-9a55-c171c7c4e520"


COMPONENTS = [
    ("#PWR1", "CONN2", "POWER_SOURCE_FLAGS", (91.44, 55.88), {"1": "+5V_MAIN", "2": "GND"}),
    ("#PWR2", "CONN2", "MCU_POWER_FLAGS", (91.44, 76.2), {"1": "+5V_U1", "2": "GND_U1"}),
    ("J1", "CONN6", "CHAIN_RING", (43.18, 55.88), {"1": "LATCH_CONN", "2": "CLOCK_CONN", "3": "DATA_CHAIN_IN", "4": "+5V_CHAIN", "5": "DATA_OUT_CHAIN", "6": "GND_CHAIN"}),
    ("U1", "ATTINY1624", "ATtiny1624-SS", (127.0, 73.66), {"1": "+5V_U1", "2": "LATCH_U1", "3": "MOTOR1", "4": "MOTOR2", "5": "MOTOR3_U1", "6": "MOTOR4", "7": "HOME", "10": "UPDI_U1", "11": "DATA_IN_U1", "12": "DATA_OUT_U1", "13": "CLOCK_U1", "14": "GND_U1"}),
    ("J3", "CONN4", "STEPPER_DRIVER_IN", (208.28, 55.88), {"1": "MOTOR1", "2": "MOTOR2", "3": "MOTOR3_DRIVER", "4": "MOTOR4"}),
    ("J4", "CONN3", "HOME_SENSOR", (208.28, 91.44), {"1": "+5V_HOME", "2": "HOME", "3": "GND"}),
    ("J5", "UPDI6", "UPDI_2X3", (170.18, 116.84), {"1": "UPDI_PROG", "2": "+5V_UPDI", "6": "GND"}),
    ("R1", "R", "10k UPDI pull-up 1206", (101.6, 111.76), {"1": "+5V_UPDI", "2": "UPDI_PROG"}),
    ("R2", "R", "10k HOME pull-up 1206", (119.38, 111.76), {"1": "+5V_HOME", "2": "HOME"}),
    ("C1", "C", "100n MCU 1206", (139.7, 106.68), {"1": "+5V_U1", "2": "GND_U1"}),
    ("C2", "C", "1n HF 1206", (157.48, 106.68), {"1": "+5V_U1", "2": "GND_U1"}),
    ("C3", "C", "10u BULK 1206", (175.26, 106.68), {"1": "+5V_UPDI", "2": "GND"}),
    ("JP1", "R", "0R CHAIN power bridge 1206", (91.44, 144.78), {"1": "+5V_CHAIN", "2": "+5V_MAIN"}),
    ("JP2", "R", "0R UPDI power bridge 1206", (114.3, 144.78), {"1": "+5V_UPDI", "2": "+5V_MAIN"}),
    ("JP3", "R", "0R HOME power bridge 1206", (137.16, 144.78), {"1": "+5V_HOME", "2": "+5V_MAIN"}),
    ("JP4", "R", "0R MCU power bridge 1206", (160.02, 144.78), {"1": "+5V_MCU_SOURCE", "2": "+5V_U1"}),
    ("JP5", "R", "INSULATED CLOCK LINK 22.3mm", (91.44, 170.18), {"1": "CLOCK_CONN", "2": "CLOCK_U1"}),
    ("JP6", "R", "0R LATCH bridge 1206", (114.3, 170.18), {"1": "LATCH_CONN", "2": "LATCH_U1"}),
    ("JP7", "R", "INSULATED DATA_IN LINK 25.6mm", (137.16, 170.18), {"1": "DATA_CHAIN_IN", "2": "DATA_IN_U1"}),
    ("JP8", "R", "0R DATA output bridge 1206", (160.02, 170.18), {"1": "DATA_OUT_U1", "2": "DATA_OUT_CHAIN"}),
    ("JP9", "R", "0R MCU ground bridge 1206", (182.88, 170.18), {"1": "GND_U1", "2": "GND"}),
    ("JP10", "R", "INSULATED UPDI LINK 16.6mm", (205.74, 170.18), {"1": "UPDI_PROG", "2": "UPDI_U1"}),
    ("JP11", "R", "INSULATED GND LINK 29.7mm", (228.6, 170.18), {"1": "GND_CHAIN", "2": "GND"}),
    ("JP12", "R", "INSULATED MOTOR3 LINK 23.5mm", (251.46, 170.18), {"1": "MOTOR3_U1", "2": "MOTOR3_DRIVER"}),
    ("JP13", "R", "INSULATED MCU POWER LINK 17.7mm", (274.32, 170.18), {"1": "+5V_MAIN", "2": "+5V_MCU_SOURCE"}),
]


PASSIVE_1206 = "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder"
CAPACITOR_1206 = "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder"
FOOTPRINTS = {
    "#PWR1": "",
    "#PWR2": "",
    "J1": "Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical_SMD",
    "J3": "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical_SMD_Pin1Left",
    "J4": "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical_SMD_Pin1Left",
    "J5": "Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical_SMD",
    "U1": "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    **{reference: PASSIVE_1206 for reference in ("R1", "R2", "JP1", "JP2", "JP3", "JP4", "JP6", "JP8", "JP9")},
    "JP5": "Alphabets:WireLink_22.3mm_SMD",
    "JP10": "Alphabets:WireLink_16.6mm_SMD",
    "JP11": "Alphabets:WireLink_29.7mm_SMD",
    "JP7": "Alphabets:WireLink_25.6mm_SMD",
    "JP12": "Alphabets:WireLink_23.5mm_SMD",
    "JP13": "Alphabets:WireLink_17.7mm_SMD",
    **{reference: CAPACITOR_1206 for reference in ("C1", "C2", "C3")},
}


NO_CONNECTS = {"U1": {"8", "9"}, "J5": {"3", "4", "5"}}
VIRTUAL_REFS = {"#PWR1", "#PWR2"}


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
        title="Alphabets V2 ATtiny1624 millable ring module",
        date="2026-08-19",
        revision="1.0",
        company="TheBeachLab / Alphabets",
        comments={
            1: "Single-sided isolation-milled module; 20 mil preferred, 16 mil minimum",
            2: "ATtiny1624 hardware SPI ring and external 28BYJ-48 driver inputs",
            3: "Microchip-compatible 2x3 UPDI header plus powered HOME sensor input",
            4: "All discrete SMD passives use 1206 packages",
        },
    )
    schematic.sheetInstances = [HierarchicalSheetInstance(instancePath="/", page="1")]

    used_symbol_names = sorted({component[1] for component in COMPONENTS})
    for name in used_symbol_names:
        embedded = copy.deepcopy(source_symbols[name])
        embedded.libId = f"attiny1624-ring:{name}"
        schematic.libSymbols.append(embedded)

    for ref, symbol_name, value, origin, net_by_pin in COMPONENTS:
        definition = source_symbols[symbol_name]
        pins = all_pins(definition)
        datasheet = next((prop.value for prop in definition.properties if prop.key == "Datasheet"), "")
        component_uuid = uid(f"component:{ref}")
        instance = SchematicSymbol(
            libraryNickname="attiny1624-ring",
            entryName=symbol_name,
            position=Position(X=origin[0], Y=origin[1], angle=0),
            unit=1,
            inBom=ref not in VIRTUAL_REFS,
            onBoard=ref not in VIRTUAL_REFS,
            dnp=False,
            fieldsAutoplaced=True,
            uuid=component_uuid,
            properties=[
                make_property("Reference", ref, origin[0], origin[1] - 22.86),
                make_property("Value", value, origin[0], origin[1] - 20.32),
                make_property("Footprint", FOOTPRINTS[ref], origin[0], origin[1], hidden=True),
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
                NoConnect(position=Position(X=pin_position[0], Y=pin_position[1]), uuid=uid(f"nc:{ref}:{number}"))
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
