<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->
# ATtiny1624 module firmware

This AVR C firmware implements revision 2 of the controller-to-module
[`protocol`](../../Protocol/PROTOCOL.md) for a 5 V ATtiny1624-SSU module.

## Implemented behavior

- Hardware `SPI0` client on `PA1/MOSI`, `PA2/MISO`, `PA3/SCK`, and `PA4/SS`.
- Byte forwarding through an arbitrary-length physical module chain.
- `0x00`, `0x01..0x40`, and automatic-home `0x41` commands.
- Active-low position-0 sensor on `PA5` with the internal pull-up enabled.
- Edge-qualified and sample-confirmed homing from either initial sensor state
  with a two-revolution travel limit.
- Present, ready, and current-position status reporting.
- Non-blocking forward-only half-step motion on `PB0..PB3` using `TCB0`.
- Wear-levelled EEPROM persistence with invalidation before movement.
- Idle sleep while SPI, latch, and motor interrupts remain serviceable.

All modules use the same binary. Chain order determines display position.

## Pin assignment

| Function | Port | SOIC-14 pin |
| --- | --- | --- |
| `LATCH / SPI0 SS` | `PA4` | 2 |
| `HOME`, active low | `PA5` | 3 |
| Motor phase 4 | `PB3` | 6 |
| Motor phase 3 | `PB2` | 7 |
| Motor phase 2 | `PB1` | 8 |
| Motor phase 1 | `PB0` | 9 |
| `UPDI` | `PA0` | 10 |
| `DATA_IN / SPI0 MOSI` | `PA1` | 11 |
| `DATA_OUT / SPI0 MISO` | `PA2` | 12 |
| `CLOCK / SPI0 SCK` | `PA3` | 13 |

The home input expects a contact or open-drain sensor between `PA5` and ground.
The motor outputs drive a ULN2003-style input stage, not the motor coils
directly. Keep the UPDI pad accessible on the production PCB.

## Position recovery

On first boot or after an interrupted movement, position commands remain
disabled until the controller sends `0x41`. The module advances forward until
it observes a fresh inactive-to-active home transition, stores position 0, and
then reports ready. If the transition is not found within two configured drum
revolutions, the phases are released and the module remains unreferenced.

The EEPROM journal contains 32 four-byte records. The firmware appends an
unknown-position record before energizing the motor and appends the completed
position after stopping. The commit byte is written last so an interrupted
write cannot become the active record.

## Motor configuration

The defaults target a 5 V 28BYJ-48 with a ULN2003-style driver:

| Setting | Default | Meaning |
| --- | --- | --- |
| `F_CPU` | `20000000UL` | Factory 20 MHz oscillator with its prescaler disabled |
| `MOTOR_HALF_STEPS_PER_REVOLUTION` | `4096UL` | Tunable output-shaft half-steps per drum revolution |
| `MOTOR_STEP_HZ` | `500UL` | Half-step rate |
| `MOTOR_REVERSED` | `0` | Set to `1` to reverse the phase sequence |
| `HOMING_MAX_REVOLUTIONS` | `2UL` | Maximum home-search travel |
| `HOME_ACTIVE_CONFIRM_STEPS` | `2u` | Consecutive active samples required at home |

The firmware distributes `MOTOR_HALF_STEPS_PER_REVOLUTION` across all 64 drum
positions, including values that are not divisible by 64. Confirm the actual
step count and direction on the assembled mechanism.

Override settings through `CPPFLAGS`, for example:

```sh
make CPPFLAGS='-DF_CPU=20000000UL -DMOTOR_HALF_STEPS_PER_REVOLUTION=4076UL -DMOTOR_REVERSED=1'
```

## Build and test

Run the portable state-machine and ring tests with the host compiler:

```sh
make test
```

Build the ATtiny1624 ELF and Intel HEX with AVR GCC:

```sh
make
```

With the keg-only Homebrew AVR GCC 15 package used for repository validation:

```sh
PATH="/opt/homebrew/opt/avr-gcc@15/bin:$PATH" make check
```

The resulting image is
`build/alphabets-v2-attiny1624-module.hex`.

Flash it through the board's UPDI connection with an avrdude programmer that
supports the ATtiny1624, for example an Atmel-ICE:

```sh
make flash PROGRAMMER=atmelice_updi
```

Use `AVRDUDE_FLAGS` for programmer-specific port settings. The firmware selects
the undivided clock at runtime and expects the factory `OSCCFG.FREQSEL=0x2`
[setting for 20 MHz](https://onlinedocs.microchip.com/oxy/GUID-7056F141-DF07-46C5-A4B8-97EB46E9B945-en-US-12/GUID-7BAFED36-9153-4AA6-BB14-C0434476E4F6.html).
After a chip erase that clears EEPROM, run `0x41` once to establish the drum
reference.
