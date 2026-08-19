# Alphabets V2 ATtiny1624 ring module

This directory contains the editable KiCad 10 design for one Alphabets V2
split-flap module. The board keeps the existing 2x3 synchronous-ring connector,
drives an external four-input stepper board, reads a powered HOME sensor, and
uses the ATtiny1624's one-wire UPDI programming interface.

The hardware assignment follows Microchip's
[ATtiny1624/1626/1627 data sheet](https://ww1.microchip.com/downloads/en/DeviceDoc/ATtiny1624-26-27-DataSheet-DS40002234B.pdf).
Microchip documents PA0 as UPDI/RESET and PA1, PA2, and PA3 as SPI0 MOSI, MISO,
and SCK respectively. The standard programming connection is the 2x3,
2.54 mm UPDI header described in Microchip's
[UPDI connection guide](https://onlinedocs.microchip.com/oxy/GUID-ACE76F82-8072-410B-AFA7-16B2BF7B4CBA-en-US-8/GUID-C59C16EC-2784-4583-8198-2780FE485FFC.html).

## Circuit

- `U1`: ATtiny1624-SS in SOIC-14.
- `J1`: 2x3 SMD ring connector for LATCH, CLOCK, serial data, +5 V, and GND.
- `J3`: four logic outputs for the external stepper driver.
- `J4`: powered three-pin HOME sensor connector with a 10 kOhm pull-up.
- `J5`: 2x3 SMD UPDI connector; pins 1, 2, and 6 carry UPDI, target VDD, and
  GND. Pins 3 through 5 are intentionally not connected.
- `R1`: 10 kOhm UPDI pull-up; `R2`: 10 kOhm HOME pull-up.
- `C1`: 100 nF local MCU decoupling; `C2`: 1 nF high-frequency bypass;
  `C3`: 10 uF board bulk capacitance.
- `JP1` through `JP4`, `JP6`, `JP8`, and `JP9`: removable 0 Ohm 1206
  links that partition power, ground, and ring signals for assembly and
  diagnosis.

The board defines this ATtiny1624 signal assignment:

| Function | MCU signal | Physical pin |
| --- | --- | ---: |
| VDD | `VDD` | 1 |
| LATCH | `PA4 / SPI0 SS` | 2 |
| Motor 1 | `PA5` | 3 |
| Motor 2 | `PA6` | 4 |
| Motor 3 | `PA7` | 5 |
| Motor 4 | `PB3` | 6 |
| HOME | `PB2` | 7 |
| UPDI | `PA0 / UPDI` | 10 |
| DATA_IN | `PA1 / SPI0 MOSI` | 11 |
| DATA_OUT | `PA2 / SPI0 MISO` | 12 |
| CLOCK | `PA3 / SPI0 SCK` | 13 |
| GND | `GND` | 14 |

`PB1` and `PB0` remain available and are intentionally not connected in this
revision. The existing ATtiny44 firmware is not reused by this hardware; the
ATtiny1624 firmware target will use SPI0 and UPDI with the mapping above.

## Connectors

| Connector | Pinout |
| --- | --- |
| `J1 CHAIN` | 1 `LATCH`, 2 `CLOCK`, 3 `DATA_IN`, 4 `+5V`, 5 `DATA_OUT`, 6 `GND` |
| `J3 DRIVER` | 1 `MOTOR1`, 2 `MOTOR2`, 3 `MOTOR3`, 4 `MOTOR4` |
| `J4 HOME` | 1 `+5V`, 2 `HOME`, 3 `GND` |
| `J5 UPDI` | 1 `UPDI`, 2 target `VDD`, 3-5 NC, 6 `GND` |

The chain connector follows [`../../../PROTOCOL.md`](../../../PROTOCOL.md):
pins 1, 2, 4, and 6 are bused, while pin 5 of one module feeds pin 3 of the
next module.

## Single-sided construction

- Finished outline: 50 x 50 mm.
- All routed copper is on `F.Cu`; the design contains no vias or back-copper
  tracks.
- Preferred tracks are 20 mil (0.508 mm). Constrained neckdowns are 16 mil
  (0.4064 mm), above the 15 mil minimum.
- Copper clearance is 0.40 mm for a 0.40 mm milling tool.
- Corners use native KiCad arcs with adaptive radii from 0.20 to 2.00 mm.
- Width transitions use curved copper tapers and routed SMD entries use curved
  teardrops.
- Every discrete resistor and capacitor uses a hand-solderable 1206 footprint.

Six insulated wire links cross above the routed copper. Solder insulated wire
between the two pads of each footprint; the dashed `F.Fab` line marks its
assembly path and is not copper:

| Reference | Signal | Pad spacing |
| --- | --- | ---: |
| `JP5` | CLOCK | 22.3 mm |
| `JP7` | DATA_IN | 25.6 mm |
| `JP10` | UPDI | 16.6 mm |
| `JP11` | chain GND | 29.7 mm |
| `JP12` | motor phase 3 | 23.5 mm |
| `JP13` | MCU power source | 17.7 mm |

## Files and reproducible validation

- `attiny1624-ring.kicad_pro`, `.kicad_sch`, and `.kicad_pcb`: editable
  native KiCad project files.
- `fabrication/`: Gerbers, drill outputs, BOM, positions, and STEP model.
- `preview/`: top render, front-copper drawing, and schematic drawing.
- `validation/`: ERC and DRC/schematic-parity reports.
- `routing/attiny1624-ring.ses`: checked-in single-layer routing session.
- `tools/`: deterministic generators, route import, organic post-processing,
  and project-specific electrical/mechanical checks.

The normal reproducible path starts from the checked-in route:

```sh
make schematic board route organic check fabrication previews
```

Set `KICAD_CLI`, `KICAD_PYTHON`, `KIUTILS_PYTHON`, and
`KICAD10_FOOTPRINT_DIR` for the installed KiCad environment. When placement or
the netlist changes, create a new session with:

```sh
make autoroute FREEROUTING_JAR=/path/to/freerouting.jar
```

`make check` enforces the 50 x 50 mm outline, front-copper-only routing, zero
vias, 16/20 mil widths, six wire links, native arcs, teardrops, zero ERC/DRC
violations, zero unrouted connections, and exact schematic-to-PCB parity.
