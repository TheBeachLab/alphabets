# Alphabets V2 ATtiny44 ring module

This directory contains the complete KiCad 10 design for one autonomous
Alphabets V2 split-flap module. The board implements the synchronous serial
ring defined in [`../../../PROTOCOL.md`](../../../PROTOCOL.md): shared `CLOCK`
and `LATCH`, regenerated forward data, and a pass-through `RETURN` conductor.

The current revision is a fabrication candidate. KiCad ERC, PCB DRC, schematic
parity, connectivity, and the generated manufacturing files are checked. The
connector keying and mechanical clearances should also be confirmed on the
first physical assembly.

## Circuit

- `U1`: ATtiny44A-SS in SOIC-14. `PA4/USCK`, `PA5/DO`, and `PA6/DI` implement
  the serial link; `PA7` is the frame latch; `PA0` through `PA3` drive the four
  motor phases; and `PB2/INT0` reads the home sensor. The assignment follows
  the [Microchip ATtiny24A/44A/84A data sheet](https://ww1.microchip.com/downloads/en/DeviceDoc/ATtiny24A-44A-84A-DataSheet-DS40002269A.pdf).
- `U2`: ULN2003A low-side Darlington driver. Its common clamp-diode pin is tied
  to `+5V`, and four channels drive the unipolar motor coils as described in
  the [ST ULN2001A/2002A/2003A/2004A data sheet](https://www.st.com/resource/en/datasheet/uln2001.pdf).
- `R1` and `C3`: 10 kOhm pull-up and 10 nF filter for the home input.
- `R2`: 10 kOhm reset pull-up.
- `C1`, `C2`, and `C4`: local logic, driver, and bulk supply decoupling.
- `J5`: standard 2x3 AVR ISP programming header.
- `TP1` and `TP2`: access to spare pins `PB0` and `PB1`.

## Connectors

| Connector | Pinout |
| --- | --- |
| `J1 CHAIN_IN` | 1 `+5V`, 2 `GND`, 3 `CLOCK`, 4 `LATCH`, 5 `DATA_IN`, 6 `RETURN` |
| `J2 CHAIN_OUT` | 1 `+5V`, 2 `GND`, 3 `CLOCK`, 4 `LATCH`, 5 `DATA_OUT`, 6 `RETURN` |
| `J3 28BYJ-48` | 1 `COIL_A`, 2 `COIL_B`, 3 `COIL_C`, 4 `COIL_D`, 5 `+5V` |
| `J4 HOME_SENSOR` | 1 `+5V`, 2 `GND`, 3 `HOME` |
| `J6 5V_INJECT` | 1 `+5V`, 2 `GND` |

`J6` injects the same regulated 5 V rail carried by the ring connectors. The
power source and wiring are sized for the connected motor and module chain.

## PCB

- 35 x 70 mm, two copper layers, nominal 1.6 mm thickness.
- Four 3.2 mm non-plated mounting holes for M3 hardware.
- Signal tracks: 0.25 mm.
- Motor-coil tracks: 0.50 mm.
- Power tracks: 1.00 mm nominal, with short neck-downs at fine-pitch pads.
- Minimum routed clearance measured by KiCad: 0.2017 mm.

The PCB is generated through KiCad's supported file and command-line APIs;
interactive GUI automation is not part of the workflow. Routing is exchanged
through Specctra DSN/SES with [Freerouting](https://github.com/freerouting/freerouting),
and all manufacturing exports use the documented [KiCad command-line interface](https://docs.kicad.org/10.0/en/cli/cli.html).

## Files

- `attiny44-ring.kicad_pro`, `.kicad_sch`, `.kicad_pcb`: editable KiCad project.
- `fabrication/gerbers/`: Gerber X2 layers plus separate PTH/NPTH drill files.
- `fabrication/attiny44-ring-bom.csv`: grouped bill of materials.
- `fabrication/attiny44-ring-positions.csv`: component positions in millimetres.
- `fabrication/attiny44-ring.step`: mechanical assembly model.
- `preview/`: top, bottom, copper, and schematic views.
- `validation/`: current ERC and DRC/parity reports.
- `tools/`: deterministic schematic, placement, routing-import, and design-check
  scripts.

## Reproduce and validate

The scripts require KiCad 10's `pcbnew` Python module. Set `KICAD_CLI`,
`KICAD_PYTHON`, and `KICAD10_FOOTPRINT_DIR` when KiCad is not installed on the
default path.

```sh
make check
```

To regenerate the placed board and route it, also set `FREEROUTING_JAR`:

```sh
make schematic board route check fabrication
```
