# Alphabets V2 ATtiny1624 module protocol

Text applications communicate with the controller through the higher-level
[`MESSAGE_PROTOCOL.md`](MESSAGE_PROTOCOL.md). This document defines revision 2
of the link between that controller and the autonomous character modules.

## Purpose

The protocol controls a physical chain of autonomous split-flap modules. Every
module contains an ATtiny1624, a four-channel unipolar stepper driver, a home
sensor, and one 64-position drum. Physical chain order is display order, and
every module runs the same firmware image.

The ATtiny44 prototype protocol remains documented in
[`PROTOCOL_V1_ATTINY44.md`](PROTOCOL_V1_ATTINY44.md).

## Physical topology

The controller and modules form a synchronous serial ring:

```text
Controller DATA_OUT -> module 1 -> module 2 -> ... -> module N -> Controller DATA_IN

Controller CLOCK  --------------------------------------> every module
Controller LATCH  --------------------------------------> every module
```

Each module exposes one 2x3 chain connector:

| Pin | Signal | Function |
| --- | --- | --- |
| 1 | `LATCH` | Shared active-low frame boundary and SPI client select |
| 2 | `CLOCK` | Shared SPI clock |
| 3 | `DATA_IN` | Serial input from the previous physical position |
| 4 | `VCC` | Regulated 5 V module supply |
| 5 | `DATA_OUT` | Regenerated serial output to the next physical position |
| 6 | `GND` | Common reference |

The harness buses pins 1, 2, 4, and 6. It connects pin 5 of module `n` to pin
3 of module `n + 1`; the final module's pin 5 returns to the controller.

## ATtiny1624 signal assignment

The production target is an ATtiny1624-SSU in the 14-pin SOIC package. The SPI
assignment uses the peripheral's default route from the
[Microchip ATtiny1624 data sheet](https://onlinedocs.microchip.com/oxy/GUID-7056F141-DF07-46C5-A4B8-97EB46E9B945-en-US-12/GUID-FB911F82-41CD-40A2-82BE-947A57ED38FB.html).

| Signal | ATtiny1624 pin |
| --- | --- |
| `DATA_IN` | `PA1 / SPI0 MOSI`, physical pin 11 |
| `DATA_OUT` | `PA2 / SPI0 MISO`, physical pin 12 |
| `CLOCK` | `PA3 / SPI0 SCK`, physical pin 13 |
| `LATCH` | `PA4 / SPI0 SS`, physical pin 2 |
| `HOME` | `PA5`, physical pin 3, active low |
| Motor phase 1 | `PB0`, physical pin 9 |
| Motor phase 2 | `PB1`, physical pin 8 |
| Motor phase 3 | `PB2`, physical pin 7 |
| Motor phase 4 | `PB3`, physical pin 6 |
| Programming/debug | `PA0 / UPDI`, physical pin 10 |
| Supply | `VDD` pin 1 and `GND` pin 14 |

`HOME` uses the ATtiny1624 internal pull-up. The sensor closes to ground at the
position-0 reference. `PA0/UPDI` is reserved for programming and debug.

## Serial format and timing

`SPI0` operates in
[client normal mode](https://onlinedocs.microchip.com/oxy/GUID-7056F141-DF07-46C5-A4B8-97EB46E9B945-en-US-12/GUID-3423A0A4-55CA-43AD-AE91-0082B72CC9A8.html):

- SPI mode 0: clock idle low, sample on rising edges.
- Most-significant bit first.
- Eight bits per byte.
- Nominal and maximum `CLOCK` frequency: 50 kHz.
- At least 20 microseconds with `CLOCK` low between consecutive bytes.
- `LATCH` idles high and acts as the active-low client-select signal.

The controller waits at least 100 microseconds after lowering `LATCH` before
the first rising clock edge. It leaves at least 20 microseconds after the final
rising clock edge before raising `LATCH`. A valid frame contains only complete
bytes.

## Frame lifecycle

A complete frame follows this sequence:

1. The controller drives `LATCH` low.
2. Every module loads its current status byte into `SPI0.DATA`.
3. The controller waits at least 100 microseconds.
4. The controller shifts one byte per module while reading the return stream.
5. Each module forwards every fully received byte during the next byte time.
6. The controller waits at least 20 microseconds and drives `LATCH` high.
7. Every module applies the final complete byte it received as its command.

This byte pipeline lets discovery continue until the controller receives its
marker without assigning addresses or fixing the chain length.

Commands are transmitted in reverse physical order. For a four-module display
whose target positions are `H O L A`, the controller transmits the command for
`A`, then `L`, then `O`, and finally `H`.

Status bytes return in reverse physical order during the same transfer. The
first returned byte belongs to the final module in the chain.

## Protocol revision selection

The controller stores one module-protocol profile for the installed chain:
`attiny1624-v2` for this protocol or `attiny44-v1` for the prototype protocol.
This keeps the shared position commands and six-wire harness while selecting
the correct `0x41` homing behavior for every module in the chain.

## Command byte

Every command byte has bit 7 cleared.

| Value | Command |
| --- | --- |
| `0x00` | Keep the current target |
| `0x01` to `0x40` | Move to drum position 0 to 63 (`position = value - 1`) |
| `0x41` | Run the automatic position-0 homing cycle |

The home cycle always searches in the normal forward direction. If `HOME` is
already active, the module first advances until the sensor releases and then
uses the next active edge, confirmed across two consecutive motor steps, as
position 0. The search is limited to two drum revolutions. A successful cycle
records position 0; an expired search stops and leaves the module unreferenced.

Drum position identifiers follow the character set selected in the controller
settings. Canonical presets and custom-profile validation are defined in
[`Code/character_sets.json`](Code/character_sets.json) and documented in
[`Code/letters.md`](Code/letters.md).

Modules are character-set agnostic: they receive only position identifiers.
The selected 64-character software sequence must match the physical flap order
installed on every connected module.

## Status byte

Every status byte has bit 7 set.

```text
bit 7      module present marker, always 1
bit 6      ready
bits 5..0  current drum position, 0 to 63
```

`ready` is cleared while the position reference is unknown, during homing or
normal movement, and while a completed position is being persisted. It is set
after the requested position is reached, the motor phases are released, and
the current position is stored.

The controller completes a display update when every module reports `ready = 1`
and its current position matches the requested position. A module that remains
unready after the motion deadline is reported as a fault at its physical
display position. The controller may retry `0x41` for an unreferenced module.

## Automatic chain discovery

The controller discovers the chain at startup and after a topology change:

1. Drive `LATCH` low.
2. Transmit `0x00` bytes and read the return stream.
3. Count every returned byte whose bit 7 is set.
4. Stop when the first transmitted `0x00` returns with bit 7 cleared.
5. Wait at least 20 microseconds, drive `LATCH` high, and store the count.

The number of status bytes before the returned marker is the chain length.
Their order runs from the final module back to the first, so the controller
reverses it for applications. A scan accepts up to 255 modules and reports a
return-path fault when the marker misses the scan deadline.

## Position persistence and recovery

At power-up, a module releases all motor phases and loads its last fully reached
position from EEPROM. The module invalidates that reference before any movement
and writes the new position only after movement completes. A power interruption
during movement therefore boots unreferenced and requires `0x41`.

Position records rotate through a 32-entry wear-levelled EEPROM journal. Each
four-byte record carries a sequence, position, integrity byte, and commit byte;
the commit byte is written last.

For a position command, the module calculates the forward distance modulo 64,
distributes the configured half-steps across the drum positions, drives the
motor asynchronously, releases the phases, persists the result, and sets
`ready`.

The firmware and build instructions are in
[`Firmware/attiny1624-module`](Firmware/attiny1624-module).

## Controller startup and update sequence

At startup, the controller:

1. Discovers the connected chain.
2. Sends `0x41` to each module that remains unready before any position request.
3. Repeats the frame until every module reports ready at position 0 or the
   homing deadline expires.

For each display message, the controller:

1. Discovers the connected chain.
2. Converts every character to its 0-to-63 drum position.
3. Transmits one command per module in reverse physical order.
4. Reads and records the returned statuses.
5. Repeats the target frame until every position is ready and matches.
6. Starts the message display interval.
