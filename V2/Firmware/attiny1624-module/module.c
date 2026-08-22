// SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
// SPDX-License-Identifier: MIT
#include <avr/eeprom.h>
#include <avr/interrupt.h>
#include <avr/io.h>
#include <avr/sleep.h>
#include <stdbool.h>
#include <stdint.h>
#include <util/atomic.h>

#include "protocol_core.h"

#ifndef F_CPU
#define F_CPU 20000000UL
#endif

#ifndef MOTOR_HALF_STEPS_PER_REVOLUTION
#define MOTOR_HALF_STEPS_PER_REVOLUTION 4096UL
#endif

#ifndef MOTOR_STEP_HZ
#define MOTOR_STEP_HZ 500UL
#endif

#ifndef MOTOR_REVERSED
#define MOTOR_REVERSED 0
#endif

#ifndef HOMING_MAX_REVOLUTIONS
#define HOMING_MAX_REVOLUTIONS 2UL
#endif

#ifndef HOME_ACTIVE_CONFIRM_STEPS
#define HOME_ACTIVE_CONFIRM_STEPS 2u
#endif

#define MOTOR_MASK 0x0fu
#define MOTOR_TIMER_CLOCK_HZ (F_CPU / 2UL)
#define MOTOR_TIMER_COMPARE_VALUE \
    ((MOTOR_TIMER_CLOCK_HZ / MOTOR_STEP_HZ) - 1UL)
#define HOMING_MAX_HALF_STEPS \
    (MOTOR_HALF_STEPS_PER_REVOLUTION * HOMING_MAX_REVOLUTIONS)
#define EEPROM_RECORD_COUNT 32u
#define EEPROM_RECORD_COMMITTED 0x5au
#define EEPROM_POSITION_UNKNOWN 0xffu

#if F_CPU != 20000000UL
#error "This firmware expects the ATtiny1624 internal 20 MHz clock"
#endif

#if MOTOR_HALF_STEPS_PER_REVOLUTION < MODULE_POSITION_COUNT
#error "MOTOR_HALF_STEPS_PER_REVOLUTION must be at least 64"
#endif

#if MOTOR_HALF_STEPS_PER_REVOLUTION > 65535UL
#error "MOTOR_HALF_STEPS_PER_REVOLUTION must fit in uint16_t"
#endif

#if HOMING_MAX_HALF_STEPS > 65535UL
#error "The homing travel limit must fit in uint16_t"
#endif

#if HOME_ACTIVE_CONFIRM_STEPS < 1u || HOME_ACTIVE_CONFIRM_STEPS > 255u
#error "HOME_ACTIVE_CONFIRM_STEPS must fit in uint8_t and be at least one"
#endif

#if MOTOR_TIMER_COMPARE_VALUE > 65535UL
#error "MOTOR_STEP_HZ is too low for TCB0 with a /2 clock"
#endif

#if MOTOR_TIMER_COMPARE_VALUE < 1UL
#error "MOTOR_STEP_HZ is too high for TCB0 with a /2 clock"
#endif

static const uint8_t motor_half_step_sequence[8] = {
    0x01u,
    0x03u,
    0x02u,
    0x06u,
    0x04u,
    0x0cu,
    0x08u,
    0x09u,
};

static volatile module_state_t module_state;

static volatile bool frame_active;
static volatile bool frame_received_byte;
static volatile bool latch_was_high;
static volatile uint8_t frame_last_byte;
static volatile bool command_pending;
static volatile uint8_t pending_command;

static volatile uint8_t motor_phase_index;
static volatile uint16_t half_steps_remaining;
static volatile uint8_t home_active_samples;

typedef struct {
    uint8_t sequence;
    uint8_t position;
    uint8_t check;
    uint8_t committed;
} position_record_t;

_Static_assert(sizeof(position_record_t) == 4u, "EEPROM record must be four bytes");

static position_record_t EEMEM eeprom_position_records[EEPROM_RECORD_COUNT];
static uint8_t last_eeprom_sequence = 0xffu;

static uint8_t position_check(uint8_t sequence, uint8_t position)
{
    return sequence ^ position ^ 0xa5u;
}

static bool load_stored_position(uint8_t *position)
{
    position_record_t newest = {0u, EEPROM_POSITION_UNKNOWN, 0u, 0u};
    bool found = false;

    for (uint8_t slot = 0u; slot < EEPROM_RECORD_COUNT; ++slot) {
        position_record_t candidate;

        eeprom_read_block(
            &candidate,
            &eeprom_position_records[slot],
            sizeof(candidate)
        );

        if (candidate.committed != EEPROM_RECORD_COMMITTED
            || candidate.check
                != position_check(candidate.sequence, candidate.position)) {
            continue;
        }

        if (!found
            || module_sequence_is_newer(candidate.sequence, newest.sequence)) {
            newest = candidate;
            found = true;
        }
    }

    if (!found) {
        return false;
    }

    last_eeprom_sequence = newest.sequence;
    if (newest.position >= MODULE_POSITION_COUNT) {
        return false;
    }

    *position = newest.position;
    return true;
}

static void append_position_record(uint8_t position)
{
    const uint8_t sequence = last_eeprom_sequence + 1u;
    position_record_t *record =
        &eeprom_position_records[sequence % EEPROM_RECORD_COUNT];

    eeprom_update_byte(&record->committed, 0u);
    eeprom_update_byte(&record->sequence, sequence);
    eeprom_update_byte(&record->position, position);
    eeprom_update_byte(&record->check, position_check(sequence, position));
    eeprom_update_byte(&record->committed, EEPROM_RECORD_COMMITTED);
    last_eeprom_sequence = sequence;
}

static void invalidate_stored_position(void)
{
    append_position_record(EEPROM_POSITION_UNKNOWN);
}

static void persist_current_position(void)
{
    uint8_t position;

    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        position = module_state.current_position;
    }

    append_position_record(position);

    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        module_mark_persisted(&module_state);
    }
}

static bool home_sensor_is_active(void)
{
    return (VPORTA.IN & PIN5_bm) == 0u;
}

static void motor_write_phase(uint8_t phase)
{
    VPORTB.OUT = (VPORTB.OUT & (uint8_t)~MOTOR_MASK)
        | (phase & MOTOR_MASK);
}

static void motor_release(void)
{
    TCB0.CTRLA = 0u;
    motor_write_phase(0u);
}

static void motor_timer_start(void)
{
    motor_write_phase(motor_half_step_sequence[motor_phase_index]);
    TCB0.CNT = 0u;
    TCB0.INTFLAGS = TCB_CAPT_bm;
    TCB0.CTRLA = TCB_CLKSEL_DIV2_gc | TCB_ENABLE_bm;
}

static void motor_start_position(void)
{
    uint8_t current_position;

    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        current_position = module_state.current_position;
    }

    half_steps_remaining = module_half_steps_to_next_position(
        current_position,
        (uint16_t)MOTOR_HALF_STEPS_PER_REVOLUTION
    );
    motor_timer_start();
}

static void motor_start_home(void)
{
    half_steps_remaining = (uint16_t)HOMING_MAX_HALF_STEPS;
    home_active_samples = 0u;
    module_home_observe(&module_state, home_sensor_is_active());
    motor_timer_start();
}

static void configure_clock(void)
{
    _PROTECTED_WRITE(CLKCTRL.MCLKCTRLB, 0u);
}

static void configure_io(void)
{
    PORTA.DIRCLR = PIN1_bm | PIN3_bm | PIN4_bm | PIN5_bm;
    PORTA.DIRSET = PIN2_bm;
    PORTA.OUTCLR = PIN2_bm;
    PORTA.PIN4CTRL = PORT_ISC_BOTHEDGES_gc;
    PORTA.PIN5CTRL = PORT_PULLUPEN_bm;
    PORTA.INTFLAGS = PIN4_bm;

    PORTB.DIRSET = MOTOR_MASK;
    PORTB.OUTCLR = MOTOR_MASK;
}

static void configure_spi(void)
{
    SPI0.CTRLA = 0u;
    SPI0.CTRLB = SPI_MODE_0_gc;
    SPI0.DATA = 0u;
    SPI0.INTFLAGS = SPI_IF_bm;
    SPI0.INTCTRL = SPI_IE_bm;
    SPI0.CTRLA = SPI_ENABLE_bm;
}

static void configure_latch_interrupt(void)
{
    latch_was_high = (VPORTA.IN & PIN4_bm) != 0u;
    PORTA.INTFLAGS = PIN4_bm;
}

static void configure_motor_timer(void)
{
    TCB0.CTRLA = 0u;
    TCB0.CTRLB = TCB_CNTMODE_INT_gc;
    TCB0.CNT = 0u;
    TCB0.CCMP = (uint16_t)MOTOR_TIMER_COMPARE_VALUE;
    TCB0.INTFLAGS = TCB_CAPT_bm;
    TCB0.INTCTRL = TCB_CAPT_bm;
}

static bool take_pending_command(uint8_t *command)
{
    bool available;

    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        available = command_pending;
        if (available) {
            *command = pending_command;
            command_pending = false;
        }
    }

    return available;
}

static void process_command(uint8_t command)
{
    module_command_result_t result;

    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        result = module_apply_command(&module_state, command);
    }

    if (result == MODULE_COMMAND_START_MOTION
        || result == MODULE_COMMAND_START_HOME) {
        invalidate_stored_position();
    }

    if (result == MODULE_COMMAND_START_MOTION) {
        motor_start_position();
    } else if (result == MODULE_COMMAND_START_HOME) {
        motor_start_home();
    }
}

ISR(PORTA_PORT_vect)
{
    const uint8_t interrupt_flags = PORTA.INTFLAGS;
    const bool latch_is_high = (VPORTA.IN & PIN4_bm) != 0u;

    PORTA.INTFLAGS = interrupt_flags;

    if ((interrupt_flags & PIN4_bm) == 0u
        || latch_is_high == latch_was_high) {
        return;
    }
    latch_was_high = latch_is_high;

    if (!latch_is_high) {
        frame_active = true;
        frame_received_byte = false;
        frame_last_byte = 0u;
        SPI0.DATA = module_build_status(&module_state);
        SPI0.INTFLAGS = SPI_IF_bm;
        return;
    }

    if (!frame_active) {
        return;
    }

    frame_active = false;
    if (frame_received_byte) {
        pending_command = frame_last_byte;
        command_pending = true;
    }
}

ISR(SPI0_INT_vect)
{
    const uint8_t received = SPI0.DATA;

    if (frame_active) {
        frame_last_byte = received;
        frame_received_byte = true;
        SPI0.DATA = received;
    } else {
        SPI0.DATA = 0u;
    }

    SPI0.INTFLAGS = SPI_IF_bm;
}

ISR(TCB0_INT_vect)
{
    TCB0.INTFLAGS = TCB_CAPT_bm;

#if MOTOR_REVERSED
    motor_phase_index = (motor_phase_index + 7u) & 0x07u;
#else
    motor_phase_index = (motor_phase_index + 1u) & 0x07u;
#endif
    motor_write_phase(motor_half_step_sequence[motor_phase_index]);

    if (module_is_homing(&module_state)) {
        const bool home_active = home_sensor_is_active();

        if (!home_active) {
            home_active_samples = 0u;
            module_home_observe(&module_state, false);
        } else if (home_active_samples < HOME_ACTIVE_CONFIRM_STEPS) {
            ++home_active_samples;
        }

        if (home_active_samples >= HOME_ACTIVE_CONFIRM_STEPS
            && module_home_observe(&module_state, true)) {
            motor_release();
            return;
        }

        if (--half_steps_remaining == 0u) {
            module_home_failed(&module_state);
            motor_release();
        }
        return;
    }

    if (--half_steps_remaining != 0u) {
        return;
    }

    if (module_reached_next_position(&module_state)) {
        motor_release();
        return;
    }

    half_steps_remaining =
        module_half_steps_to_next_position(
            module_state.current_position,
            (uint16_t)MOTOR_HALF_STEPS_PER_REVOLUTION
        );
}

static void sleep_until_work(void)
{
    cli();
    if (!command_pending
        && !(module_needs_persist(&module_state)
            && !module_is_moving(&module_state))) {
        sleep_enable();
        sei();
        sleep_cpu();
        sleep_disable();
        return;
    }
    sei();
}

int main(void)
{
    uint8_t stored_position = 0u;
    uint8_t command;
    const bool stored_position_is_valid = load_stored_position(&stored_position);

    configure_clock();
    configure_io();
    module_state_init(&module_state, stored_position, stored_position_is_valid);
    motor_release();
    configure_motor_timer();
    configure_spi();
    configure_latch_interrupt();

    set_sleep_mode(SLEEP_MODE_IDLE);
    sei();

    for (;;) {
        if (take_pending_command(&command)) {
            process_command(command);
        }

        if (module_needs_persist(&module_state)
            && !module_is_moving(&module_state)) {
            persist_current_position();
        }

        sleep_until_work();
    }
}
