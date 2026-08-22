// SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
// SPDX-License-Identifier: MIT
#include <assert.h>
#include <stddef.h>
#include <stdio.h>

#include "protocol_core.h"

static void test_uncalibrated_boot_requires_calibration(void)
{
    module_state_t state;

    module_state_init(&state, 0u, false);
    assert(module_build_status(&state) == MODULE_STATUS_PRESENT);
    assert(module_apply_command(&state, 4u) == MODULE_COMMAND_IGNORED);
    assert(!module_is_moving(&state));

    assert(
        module_apply_command(&state, MODULE_COMMAND_CALIBRATE_ZERO)
        == MODULE_COMMAND_CALIBRATED
    );
    assert(module_build_status(&state) == MODULE_STATUS_PRESENT);
    module_mark_persisted(&state);
    assert(
        module_build_status(&state)
        == (MODULE_STATUS_PRESENT | MODULE_STATUS_READY)
    );
}

static void test_forward_move_and_ready_status(void)
{
    module_state_t state;

    module_state_init(&state, 0u, true);
    assert(module_apply_command(&state, 4u) == MODULE_COMMAND_START_MOTION);
    assert(module_build_status(&state) == MODULE_STATUS_PRESENT);

    assert(!module_reached_next_position(&state));
    assert(state.current_position == 1u);
    assert(!module_reached_next_position(&state));
    assert(state.current_position == 2u);
    assert(module_reached_next_position(&state));
    assert(state.current_position == 3u);
    assert(module_build_status(&state) == (MODULE_STATUS_PRESENT | 3u));

    module_mark_persisted(&state);
    assert(
        module_build_status(&state)
        == (MODULE_STATUS_PRESENT | MODULE_STATUS_READY | 3u)
    );
}

static void test_forward_wrap(void)
{
    module_state_t state;

    module_state_init(&state, 63u, true);
    assert(module_apply_command(&state, 2u) == MODULE_COMMAND_START_MOTION);
    assert(!module_reached_next_position(&state));
    assert(state.current_position == 0u);
    assert(module_reached_next_position(&state));
    assert(state.current_position == 1u);
}

static void test_retarget_while_moving(void)
{
    module_state_t state;

    module_state_init(&state, 63u, true);
    assert(module_apply_command(&state, 3u) == MODULE_COMMAND_START_MOTION);
    assert(module_apply_command(&state, 1u) == MODULE_COMMAND_ACCEPTED);
    assert(module_reached_next_position(&state));
    assert(state.current_position == 0u);
}

static void test_keep_and_invalid_commands_do_not_change_target(void)
{
    module_state_t state;

    module_state_init(&state, 7u, true);
    assert(
        module_apply_command(&state, MODULE_COMMAND_KEEP)
        == MODULE_COMMAND_ACCEPTED
    );
    assert(module_apply_command(&state, 0x42u) == MODULE_COMMAND_IGNORED);
    assert(module_apply_command(&state, 0xffu) == MODULE_COMMAND_IGNORED);
    assert(state.current_position == 7u);
    assert(state.target_position == 7u);
}

static void test_calibration_is_ignored_during_motion(void)
{
    module_state_t state;

    module_state_init(&state, 10u, true);
    assert(module_apply_command(&state, 20u) == MODULE_COMMAND_START_MOTION);
    assert(
        module_apply_command(&state, MODULE_COMMAND_CALIBRATE_ZERO)
        == MODULE_COMMAND_IGNORED
    );
    assert(state.current_position == 10u);
}

static uint8_t shift_chain_byte(
    uint8_t *registers,
    size_t module_count,
    uint8_t controller_output
)
{
    uint8_t forwarded = controller_output;

    for (size_t module = 0u; module < module_count; ++module) {
        const uint8_t module_output = registers[module];
        registers[module] = forwarded;
        forwarded = module_output;
    }

    return forwarded;
}

static void test_ring_order(size_t module_count)
{
    uint8_t registers[255];
    uint8_t commands[255];

    for (size_t module = 0u; module < module_count; ++module) {
        registers[module] = MODULE_STATUS_PRESENT
            | (uint8_t)(module & MODULE_STATUS_POSITION_MASK);
        commands[module] = (uint8_t)(module % MODULE_POSITION_COUNT) + 1u;
    }

    for (size_t transfer = 0u; transfer < module_count; ++transfer) {
        const uint8_t returned = shift_chain_byte(
            registers,
            module_count,
            commands[module_count - transfer - 1u]
        );
        const size_t expected_module = module_count - transfer - 1u;
        assert((returned & MODULE_STATUS_PRESENT) != 0u);
        assert(
            (returned & MODULE_STATUS_POSITION_MASK)
            == (expected_module & MODULE_STATUS_POSITION_MASK)
        );
    }

    for (size_t module = 0u; module < module_count; ++module) {
        assert(registers[module] == commands[module]);
    }
}

static void test_ring_discovery(size_t module_count)
{
    uint8_t registers[255];
    size_t discovered = 0u;

    for (size_t module = 0u; module < module_count; ++module) {
        registers[module] = MODULE_STATUS_PRESENT | MODULE_STATUS_READY;
    }

    for (;;) {
        const uint8_t returned = shift_chain_byte(
            registers,
            module_count,
            MODULE_COMMAND_KEEP
        );
        if ((returned & MODULE_STATUS_PRESENT) == 0u) {
            break;
        }
        ++discovered;
        assert(discovered <= 255u);
    }

    assert(discovered == module_count);
}

static void test_ring_sizes(void)
{
    static const size_t sizes[] = {1u, 4u, 16u, 255u};

    for (size_t index = 0u; index < sizeof(sizes) / sizeof(sizes[0]); ++index) {
        test_ring_order(sizes[index]);
        test_ring_discovery(sizes[index]);
    }
}

static void test_fractional_position_steps_cover_one_revolution(void)
{
    uint32_t total = 0u;
    uint16_t minimum = UINT16_MAX;
    uint16_t maximum = 0u;

    for (uint8_t position = 0u; position < MODULE_POSITION_COUNT; ++position) {
        const uint16_t steps =
            module_half_steps_to_next_position(position, 4076u);
        total += steps;
        if (steps < minimum) {
            minimum = steps;
        }
        if (steps > maximum) {
            maximum = steps;
        }
    }

    assert(total == 4076u);
    assert(minimum == 63u);
    assert(maximum == 64u);
}

static void test_eeprom_sequence_wrap_order(void)
{
    assert(module_sequence_is_newer(1u, 0u));
    assert(module_sequence_is_newer(0u, 255u));
    assert(module_sequence_is_newer(3u, 250u));
    assert(!module_sequence_is_newer(250u, 3u));
    assert(!module_sequence_is_newer(42u, 42u));
}

int main(void)
{
    test_uncalibrated_boot_requires_calibration();
    test_forward_move_and_ready_status();
    test_forward_wrap();
    test_retarget_while_moving();
    test_keep_and_invalid_commands_do_not_change_target();
    test_calibration_is_ignored_during_motion();
    test_ring_sizes();
    test_fractional_position_steps_cover_one_revolution();
    test_eeprom_sequence_wrap_order();
    puts("protocol core tests passed");
    return 0;
}
