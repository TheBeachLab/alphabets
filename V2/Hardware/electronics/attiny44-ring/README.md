# Alphabets V2 ATtiny44 SPI-ring module

This directory contains the editable KiCad 10 design for one Alphabets V2
split-flap module. The ATtiny44 participates in the synchronous serial ring
defined in [`../../../PROTOCOL.md`](../../../PROTOCOL.md) and drives the four
logic inputs of the external stepper-driver board supplied with the motor.

## Circuit

- `U1`: ATtiny44A-SS in SOIC-14.
- `J1`: one 2x3, 2.54 mm, surface-mount chain connector.
- `J5`: one standard 2x3, 2.54 mm, surface-mount AVR ISP connector.
- `J3`: four logic outputs for `IN1` through `IN4` on the external driver.
- `R2`: 10 kOhm reset pull-up in 1206.
- `C1`: 100 nF MCU decoupling capacitor in 1206.
- `C2`: 10 uF bulk capacitor in 1206.
- `JP5`, `JP6`, `JP7`, `JP8`, and `JP16` through `JP20`: 0 Ohm 1206 links
  used as physical copper bridges.

The ATtiny44 signal assignment follows the
[Microchip ATtiny24A/44A/84A data sheet](https://ww1.microchip.com/downloads/en/DeviceDoc/ATtiny24A-44A-84A-DataSheet-DS40002269A.pdf).

## Connectors

| Connector | Pinout |
| --- | --- |
| `J1 CHAIN` | 1 `LATCH`, 2 `CLOCK`, 3 `DATA_IN`, 4 `+5V`, 5 `DATA_OUT`, 6 `GND` |
| `J3 DRIVER` | 1 `IN1`, 2 `IN2`, 3 `IN3`, 4 `IN4` |
| `J5 ISP` | 1 `MISO`, 2 `+5V`, 3 `SCK`, 4 `MOSI`, 5 `RESET`, 6 `GND` |

The chain harness buses pins 1, 2, 4, and 6. It connects pin 5 of each module
to pin 3 of the following module. The external motor-driver board shares the
regulated 5 V supply and ground with this module.

## Milling rules

- Board outline: 80 x 90 mm.
- All routed copper is on `F.Cu`.
- Every track is at least 18 mil (0.4572 mm).
- Routed clearance is 0.40 mm for a 0.40 mm milling bit.
- Crossings use 0 Ohm 1206 links.
- All discrete SMD passives use 1206 footprints.
- Four 3.2 mm non-plated M3 mounting holes are provided.

## Files and validation

- `attiny44-ring.kicad_pro`, `.kicad_sch`, and `.kicad_pcb`: editable native
  KiCad project files.
- `fabrication/`: front-copper Gerbers, drill data, BOM, positions, and STEP.
- `preview/`: rendered top, copper, and schematic views.
- `validation/`: current ERC and DRC/schematic-parity reports.
- `tools/`: deterministic schematic, board, single-layer routing, and design
  checks.

The workflow uses native files and command-line validation rather than GUI
automation. To reproduce the placed and routed board, set the KiCad paths and
`FREEROUTING_JAR`, then run:

```sh
make schematic board route check fabrication previews
```
