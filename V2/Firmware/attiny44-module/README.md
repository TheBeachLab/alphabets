<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->
# ATtiny44A module firmware

This AVR C firmware implements the controller-to-module protocol in
[`prototype protocol`](../../Protocol/PROTOCOL_V1_ATTINY44.md) for the
[`ATtiny44 ring board`](../../Hardware/Prototype/electronics/attiny44-ring)
board.

## Implemented behavior

- ATtiny44A USI three-wire slave on `PA6/DI`, `PA5/DO`, and `PA4/USCK`.
- `PA7` pin-change interrupt for the active-low frame `LATCH`.
- Byte forwarding through an arbitrary-length physical module chain.
- Rejection of frames that end between byte boundaries.
- `0x00`, `0x01..0x40`, and `0x41` command handling.
- Present, ready, and current-position status byte generation.
- Non-blocking forward-only half-step motion on `PA0..PA3`.
- Timer-driven movement while USI frames continue to be serviced.
- Wear-levelled EEPROM persistence of the last fully reached position.
- EEPROM invalidation before movement, so interrupted motion requires a new
  manual position-0 reference instead of reporting a stale position as ready.

All modules use the same binary. Chain order determines display position.

## Position reference on the current PCB

The current `attiny44-ring` PCB leaves `PB2/HOME` unconnected. On first boot,
after interrupted motion, or after mechanically changing a drum:

1. Leave the module powered and stationary.
2. Align the drum so its installed character position 0 is visible.
3. Send command `0x41` to that module.
4. Wait until its status reports `ready = 1` at position 0.

The calibration command records the reference in EEPROM without moving the
motor. Position commands are ignored while the reference is unknown.

Position state uses a 32-record EEPROM journal. The firmware appends an
unreferenced record before energizing the motor and appends the completed
position afterward. The commit byte is written last, so a partially written
record is ignored at the next boot.

## Motor configuration

The defaults target a 5 V 28BYJ-48 with its ULN2003-style driver:

| Setting | Default | Meaning |
| --- | --- | --- |
| `F_CPU` | `8000000UL` | Internal CPU clock after clearing `CLKPR` |
| `MOTOR_HALF_STEPS_PER_REVOLUTION` | `4096UL` | Tunable output-shaft half-steps per drum revolution |
| `MOTOR_STEP_HZ` | `500UL` | Half-step rate |
| `MOTOR_REVERSED` | `0` | Set to `1` to reverse the phase sequence |

The firmware distributes `MOTOR_HALF_STEPS_PER_REVOLUTION` across all 64 drum
positions, including values that are not divisible by 64. Confirm the actual
step count and direction on the assembled mechanism before running long message
sequences.

Override a setting through `CPPFLAGS`, for example:

```sh
make CPPFLAGS='-DF_CPU=8000000UL -DMOTOR_HALF_STEPS_PER_REVOLUTION=4076UL -DMOTOR_REVERSED=1'
```

## Build and test

Run the portable protocol state-machine tests with the host C compiler:

```sh
make test
```

The tests cover command/status behavior, forward wraparound, fractional motor
steps, and command/status ordering plus discovery for 1, 4, 16, and 255
modules.

Build the ATtiny44A ELF and Intel HEX with AVR GCC:

```sh
make
```

With the keg-only Homebrew AVR GCC 15 package used for repository validation:

```sh
PATH="/opt/homebrew/opt/avr-gcc@15/bin:$PATH" make check
```

Flash through the board's AVR ISP connector:

```sh
make flash PROGRAMMER=usbtiny
```

The flash target requires `avrdude`. `AVRDUDE_FLAGS` can provide a port or other
programmer-specific settings. The target does not change fuses. The firmware
selects the undivided internal 8 MHz clock at runtime through `CLKPR`.
