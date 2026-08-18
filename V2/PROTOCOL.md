# Alphabets V2 module protocol

Text applications communicate with the controller through the higher-level
[`MESSAGE_PROTOCOL.md`](MESSAGE_PROTOCOL.md). This document defines the link
between that controller and the autonomous character modules.

## Purpose

The Alphabets V2 protocol controls a physical chain of autonomous split-flap
modules. Each module contains an ATtiny44, an external unipolar stepper-driver
board, and one 64-position drum.

The physical position of a module in the chain is its display position. Every
module runs the same firmware.

## Physical topology

The controller and modules form a synchronous serial ring:

```text
Controller DATA_OUT -> module 1 -> module 2 -> ... -> module N -> Controller DATA_IN

Controller CLOCK  --------------------------------------> every module
Controller LATCH  --------------------------------------> every module
```

Each module exposes one 2x3 SMD chain connector. The chain harness uses these
six pins:

| Pin | Signal | Function |
| --- | --- | --- |
| 1 | `LATCH` | Shared frame boundary |
| 2 | `CLOCK` | Shared serial clock |
| 3 | `DATA_IN` | Serial input from the previous physical position |
| 4 | `VCC` | Regulated 5 V module supply |
| 5 | `DATA_OUT` | Regenerated serial output to the next physical position |
| 6 | `GND` | Common reference |

The harness buses pins 1, 2, 4, and 6. It connects pin 5 of module `n` to pin
3 of module `n + 1`; the final module's pin 5 returns to the controller.

## ATtiny44 signal assignment

| Signal | ATtiny44 pin |
| --- | --- |
| `DATA_IN` | `PA6 / DI`, physical pin 7 |
| `DATA_OUT` | `PA5 / DO`, physical pin 8 |
| `CLOCK` | `PA4 / USCK`, physical pin 9 |
| `LATCH` | `PA7`, physical pin 6 |
| Motor phase 1 | `PA0`, physical pin 13 |
| Motor phase 2 | `PA1`, physical pin 12 |
| Motor phase 3 | `PA2`, physical pin 11 |
| Motor phase 4 | `PA3`, physical pin 10 |
| Reset | `PB3 / RESET`, physical pin 4 |

The Universal Serial Interface operates in three-wire slave mode. Data is
transferred most-significant bit first. `CLOCK` idles low and each rising edge
shifts one bit. The nominal clock frequency is 50 kHz.

## Frame lifecycle

`LATCH` idles high. A complete frame follows this sequence:

1. The controller drives `LATCH` low.
2. Every module loads its status byte into its serial register.
3. The controller waits at least 100 microseconds.
4. The controller shifts one byte per module while reading the return stream.
5. The controller drives `LATCH` high.
6. Every module validates and applies the command byte now held in its serial
   register.

Commands are transmitted in reverse physical order. For a four-module display
whose target positions are `H O L A`, the controller transmits the command for
`A`, then `L`, then `O`, and finally `H`.

Status bytes return in reverse physical order during the same transfer. The
first returned byte belongs to the final module in the chain.

## Command byte

Every command byte has bit 7 cleared.

| Value | Command |
| --- | --- |
| `0x00` | Keep the current target |
| `0x01` to `0x40` | Move to drum position 0 to 63 (`position = value - 1`) |

Drum position identifiers follow the character set selected in the controller
settings. Canonical presets and custom-profile validation are defined in
[`Code/character_sets.json`](Code/character_sets.json) and documented in
[`Code/letters.md`](Code/letters.md).

Modules are character-set agnostic: they receive only position identifiers.
The selected 64-character software sequence must therefore match the physical
flap order installed on every connected module. Changing a preset changes the
text-to-position mapping, not the command-byte format.

## Status byte

Every status byte has bit 7 set.

```text
bit 7      module present marker, always 1
bit 6      ready
bits 5..0  current drum position, 0 to 63
```

`ready` is cleared while the module is moving. It is set after the requested
drum position has been reached and the motor phases have been released.

The controller completes a display update when every module reports `ready = 1`
and its current position matches the requested position. It repeats the target
frame while modules are moving. A module whose status misses the update deadline
is reported as a module fault at its physical display position.

## Automatic chain discovery

The controller discovers the chain at startup and after a topology change:

1. It starts a frame by driving `LATCH` low.
2. Every module loads a status byte with bit 7 set.
3. The controller transmits `0x00` command bytes and reads returned bytes.
4. Each returned byte with bit 7 set counts one physical module.
5. The controller's first `0x00` byte eventually returns with bit 7 cleared and
   marks the end of the module sequence.
6. The controller drives `LATCH` high and stores the discovered module count.

The number of status bytes before the returned command byte is the chain length.
Their order defines display positions from the final module back to the first;
the controller reverses that order when presenting positions to applications.

The controller performs discovery at startup, before every display message,
after a return-path timeout, and after the chain harness is reconnected. A
discovery scan accepts up to 255 modules and reports a return-path fault when
its command marker misses the scan deadline.

## Module motion state

At power-up, a module releases all four motor phases and initializes its serial
register and position state.

For a position command, the module calculates the forward distance modulo 64,
drives the external unipolar stepper board through that number of positions,
releases the motor phases, records the new current position, and sets `ready`.

## Controller update sequence

For each display message, the controller:

1. Discovers the connected module chain.
2. Converts every character to its 0-to-63 drum position.
3. Builds one command byte per discovered module.
4. Transmits the commands in reverse physical order.
5. Reads and records the returned module statuses.
6. Repeats the target frame until all positions are ready and match.
7. Starts the message display interval.
