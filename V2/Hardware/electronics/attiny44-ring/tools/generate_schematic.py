#!/usr/bin/env python3
"""Generate the millable Alphabets V2 ATtiny44 ring schematic."""

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
    ("#PWR1", "CONN2", "POWER_SOURCE_FLAGS", (91.44, 55.88), {"1": "+5V_U1", "2": "GND"}),
    ("J1", "CONN6", "CHAIN_RING", (43.18, 55.88), {"1": "LATCH_CONN", "2": "CLOCK_TOP", "3": "DATA_CHAIN_IN", "4": "+5V_CHAIN", "5": "DATA_OUT_CHAIN", "6": "GND"}),
    ("U1", "ATTINY44A", "ATtiny44A-SS", (127.0, 73.66), {"1": "+5V_U1", "4": "RESET", "6": "LATCH_A", "7": "DATA_IN", "8": "DATA_OUT_A", "9": "CLOCK_U1", "10": "MOTOR4", "11": "MOTOR3", "12": "MOTOR2", "13": "MOTOR1", "14": "GND"}),
    ("J3", "CONN4", "STEPPER_DRIVER_IN", (208.28, 60.96), {"1": "MOTOR1", "2": "MOTOR2", "3": "MOTOR3", "4": "MOTOR4"}),
    ("J5", "ISP6", "AVR_ISP_2X3", (170.18, 116.84), {"1": "DATA_OUT_A", "2": "ISP_VCC", "3": "CLOCK_ISP", "4": "DATA_IN", "5": "RESET_ISP", "6": "GND"}),
    ("R2", "R", "10k RESET pull-up 1206", (111.76, 101.6), {"1": "+5V", "2": "RESET"}),
    ("C1", "C", "100n MCU 1206", (134.62, 106.68), {"1": "+5V_U1", "2": "GND"}),
    ("C2", "C", "10u BULK 1206", (152.4, 106.68), {"1": "+5V_TOP", "2": "GND"}),
    ("JP5", "R", "0R CLOCK input jumper 1206", (91.44, 144.78), {"1": "CLOCK_TOP", "2": "CLOCK_A"}),
    ("JP6", "R", "0R LATCH input jumper 1206", (114.3, 144.78), {"1": "LATCH_TOP", "2": "LATCH_A"}),
    ("JP7", "R", "0R DATA input jumper 1206", (137.16, 144.78), {"1": "DATA_IN", "2": "DATA_TOP"}),
    ("JP8", "R", "0R CHAIN DATA_OUT jumper 1206", (160.02, 144.78), {"1": "DATA_OUT_A", "2": "DATA_OUT_CHAIN"}),
    ("JP16", "R", "0R CLOCK MCU bridge 1206", (205.74, 157.48), {"1": "CLOCK_A", "2": "CLOCK_U1"}),
    ("JP17", "R", "0R DATA chain bridge 1206", (228.6, 157.48), {"1": "DATA_CHAIN_IN", "2": "DATA_TOP"}),
    ("JP18", "R", "0R MCU power bridge 1206", (251.46, 157.48), {"1": "+5V", "2": "+5V_U1"}),
    ("JP19", "R", "0R CHAIN power bridge 1206", (91.44, 170.18), {"1": "+5V_CHAIN", "2": "+5V_TOP"}),
    ("JP20", "R", "0R ISP VCC bridge 1206", (114.3, 170.18), {"1": "ISP_VCC", "2": "+5V_TOP"}),
    ("JP21", "R", "0R POWER crossover 1 1206", (137.16, 170.18), {"1": "+5V_MID", "2": "+5V_TOP"}),
    ("JP22", "R", "0R LATCH crossover 1206", (160.02, 170.18), {"1": "LATCH_CONN", "2": "LATCH_TOP"}),
    ("JP23", "R", "0R POWER crossover 2 1206", (182.88, 170.18), {"1": "+5V", "2": "+5V_MID"}),
    ("JP24", "R", "0R ISP RESET crossover 1206", (205.74, 170.18), {"1": "RESET_ISP", "2": "RESET"}),
    ("JP25", "R", "0R ISP SCK crossover 1206", (228.6, 170.18), {"1": "CLOCK_ISP", "2": "CLOCK_U1"}),
]


FOOTPRINTS = {
    "#PWR1": "",
    "J1": "Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical_SMD",
    "J3": "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical_SMD_Pin1Left",
    "J5": "Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical_SMD",
    "U1": "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    "R2": "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder",
    "C1": "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder",
    "C2": "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder",
    "JP5": "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder",
    "JP6": "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder",
    "JP7": "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder",
    "JP8": "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder",
    "JP16": "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder",
    "JP17": "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder",
    "JP18": "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder",
    "JP19": "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder",
    "JP20": "Alphabets:R_1206_3216Metric_CompactCrossover",
    "JP21": "Alphabets:R_1206_3216Metric_CompactCrossover",
    "JP22": "Alphabets:R_1206_3216Metric_CompactCrossover",
    "JP23": "Alphabets:R_1206_3216Metric_CompactCrossover",
    "JP24": "Alphabets:R_1206_3216Metric_CompactCrossover",
    "JP25": "Alphabets:R_1206_3216Metric_CompactCrossover",
}


NO_CONNECTS = {"U1": {"2", "3", "5"}}
VIRTUAL_REFS = {"#PWR1"}


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
    conn4 = copy.deepcopy(source_symbols["CONN5"])
    conn4.libId = "CONN4"
    for unit in conn4.units:
        unit.pins = [pin for pin in unit.pins if str(pin.number) != "5"]
    source_symbols["CONN4"] = conn4
    if not any(symbol.libId == "CONN4" for symbol in library.symbols):
        library.symbols.append(copy.deepcopy(conn4))
        library.to_file(str(symbol_path), encoding="utf-8")

    schematic = Schematic.create_new()
    schematic.version = "20231120"
    schematic.generator = "alphabets_v2_generator"
    schematic.uuid = SCHEMATIC_UUID
    schematic.titleBlock = TitleBlock(
        title="Alphabets V2 ATtiny44 millable ring module",
        date="2026-08-15",
        revision="2.0",
        company="TheBeachLab / Alphabets",
        comments={
            1: "Single-sided isolation-milled module; 16 mil minimum tracks",
            2: "External 28BYJ-48 driver board logic inputs: IN1..IN4",
            3: "One CHAIN_RING and one AVR ISP use 2x3 2.54 mm SMD headers",
            4: "All discrete SMD passives use 1206 packages",
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
        datasheet = next((prop.value for prop in definition.properties if prop.key == "Datasheet"), "")
        component_uuid = uid(f"component:{ref}")
        instance = SchematicSymbol(
            libraryNickname="attiny44-ring",
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
