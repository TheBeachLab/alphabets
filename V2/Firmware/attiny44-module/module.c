#include <avr/eeprom.h>
#include <avr/interrupt.h>
#include <avr/io.h>
#include <avr/sleep.h>
#include <stdbool.h>
#include <stdint.h>
#include <util/atomic.h>

#include "protocol_core.h"

#ifndef F_CPU
#define F_CPU 8000000UL
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

#define MOTOR_MASK 0x0fu
#define TIMER0_PRESCALER 64UL
#define TIMER0_COMPARE_VALUE ((F_CPU / TIMER0_PRESCALER / MOTOR_STEP_HZ) - 1UL)
#define EEPROM_RECORD_COUNT 32u
#define EEPROM_RECORD_COMMITTED 0x5au
#define EEPROM_POSITION_UNKNOWN 0xffu

#if F_CPU != 8000000UL
#error "This firmware expects the ATtiny44A internal 8 MHz clock"
#endif

#if MOTOR_HALF_STEPS_PER_REVOLUTION < MODULE_POSITION_COUNT
#error "MOTOR_HALF_STEPS_PER_REVOLUTION must be at least 64"
#endif

#if MOTOR_HALF_STEPS_PER_REVOLUTION > 65535UL
#error "MOTOR_HALF_STEPS_PER_REVOLUTION must fit in uint16_t"
#endif

#if TIMER0_COMPARE_VALUE > 255UL
#error "MOTOR_STEP_HZ is too low for Timer/Counter0 with a /64 prescaler"
#endif

#if TIMER0_COMPARE_VALUE < 1UL
#error "MOTOR_STEP_HZ is too high for Timer/Counter0 with a /64 prescaler"
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

static void motor_write_phase(uint8_t phase)
{
    PORTA = (PORTA & (uint8_t)~MOTOR_MASK) | (phase & MOTOR_MASK);
}

static void motor_release(void)
{
    TCCR0B = 0u;
    motor_write_phase(0u);
}

static void motor_start(void)
{
    uint8_t current_position;

    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        current_position = module_state.current_position;
    }

    half_steps_remaining = module_half_steps_to_next_position(
        current_position,
        (uint16_t)MOTOR_HALF_STEPS_PER_REVOLUTION
    );
    motor_write_phase(motor_half_step_sequence[motor_phase_index]);
    TCNT0 = 0u;
    TIFR0 = _BV(OCF0A);
    TCCR0B = _BV(CS01) | _BV(CS00);
}

static void usi_complete_byte(void)
{
    const uint8_t received = USIBR;

    frame_last_byte = received;
    frame_received_byte = true;
    USIDR = received;
    USISR = _BV(USIOIF);
}

static void configure_clock(void)
{
    CLKPR = _BV(CLKPCE);
    CLKPR = 0u;
}

static void configure_io(void)
{
    DDRA = (DDRA & (uint8_t)~(_BV(PA4) | _BV(PA6) | _BV(PA7)))
        | MOTOR_MASK | _BV(PA5);
    PORTA &= (uint8_t)~(
        MOTOR_MASK | _BV(PA4) | _BV(PA5) | _BV(PA6) | _BV(PA7)
    );

    DDRB &= (uint8_t)~_BV(PB2);
    PORTB &= (uint8_t)~_BV(PB2);
}

static void configure_usi(void)
{
    USIDR = 0u;
    USISR = _BV(USISIF) | _BV(USIOIF);
    USICR = _BV(USIOIE) | _BV(USIWM0) | _BV(USICS1);
}

static void configure_latch_interrupt(void)
{
    latch_was_high = (PINA & _BV(PA7)) != 0u;
    GIFR = _BV(PCIF0);
    PCMSK0 = _BV(PCINT7);
    GIMSK |= _BV(PCIE0);
}

static void configure_motor_timer(void)
{
    TCCR0A = _BV(WGM01);
    TCCR0B = 0u;
    TCNT0 = 0u;
    OCR0A = (uint8_t)TIMER0_COMPARE_VALUE;
    TIFR0 = _BV(OCF0A);
    TIMSK0 = _BV(OCIE0A);
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
        || result == MODULE_COMMAND_CALIBRATED) {
        invalidate_stored_position();
    }

    if (result == MODULE_COMMAND_START_MOTION) {
        motor_start();
    }
}

ISR(PCINT0_vect)
{
    const bool latch_is_high = (PINA & _BV(PA7)) != 0u;

    if (latch_is_high == latch_was_high) {
        return;
    }
    latch_was_high = latch_is_high;

    if (!latch_is_high) {
        frame_active = true;
        frame_received_byte = false;
        frame_last_byte = 0u;
        USIDR = module_build_status(&module_state);
        USISR = _BV(USISIF) | _BV(USIOIF);
        return;
    }

    if (!frame_active) {
        return;
    }

    if ((USISR & _BV(USIOIF)) != 0u) {
        usi_complete_byte();
    }

    frame_active = false;
    if (frame_received_byte && (USISR & 0x0fu) == 0u) {
        pending_command = frame_last_byte;
        command_pending = true;
    }
}

ISR(USI_OVF_vect)
{
    if (frame_active) {
        usi_complete_byte();
    } else {
        USIDR = 0u;
        USISR = _BV(USIOIF);
    }
}

ISR(TIM0_COMPA_vect)
{
#if MOTOR_REVERSED
    motor_phase_index = (motor_phase_index + 7u) & 0x07u;
#else
    motor_phase_index = (motor_phase_index + 1u) & 0x07u;
#endif
    motor_write_phase(motor_half_step_sequence[motor_phase_index]);

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
    configure_usi();
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
