// SPDX-License-Identifier: MIT
#include "protocol_core.h"

static bool flag_is_set(const volatile module_state_t *state, uint8_t flag)
{
    return (state->flags & flag) != 0u;
}

void module_state_init(
    volatile module_state_t *state,
    uint8_t stored_position,
    bool stored_position_is_valid
)
{
    const uint8_t position = stored_position & MODULE_STATUS_POSITION_MASK;

    state->current_position = position;
    state->target_position = position;
    state->flags = stored_position_is_valid ? MODULE_FLAG_CALIBRATED : 0u;
}

uint8_t module_build_status(const volatile module_state_t *state)
{
    uint8_t status = MODULE_STATUS_PRESENT;

    if (module_is_calibrated(state) && !module_is_moving(state)
        && !module_needs_persist(state)) {
        status |= MODULE_STATUS_READY;
    }

    status |= state->current_position & MODULE_STATUS_POSITION_MASK;
    return status;
}

module_command_result_t module_apply_command(
    volatile module_state_t *state,
    uint8_t command
)
{
    if (command == MODULE_COMMAND_KEEP) {
        return MODULE_COMMAND_ACCEPTED;
    }

    if (command == MODULE_COMMAND_CALIBRATE_ZERO) {
        if (module_is_moving(state)) {
            return MODULE_COMMAND_IGNORED;
        }

        state->current_position = 0u;
        state->target_position = 0u;
        state->flags = MODULE_FLAG_CALIBRATED | MODULE_FLAG_PERSIST_PENDING;
        return MODULE_COMMAND_CALIBRATED;
    }

    if (command < MODULE_COMMAND_POSITION_FIRST
        || command > MODULE_COMMAND_POSITION_LAST
        || !module_is_calibrated(state)) {
        return MODULE_COMMAND_IGNORED;
    }

    state->target_position = command - MODULE_COMMAND_POSITION_FIRST;

    if (module_is_moving(state) || state->target_position == state->current_position) {
        return MODULE_COMMAND_ACCEPTED;
    }

    state->flags |= MODULE_FLAG_MOVING | MODULE_FLAG_PERSIST_PENDING;
    return MODULE_COMMAND_START_MOTION;
}

bool module_reached_next_position(volatile module_state_t *state)
{
    state->current_position =
        (state->current_position + 1u) & MODULE_STATUS_POSITION_MASK;

    if (state->current_position != state->target_position) {
        return false;
    }

    state->flags &= (uint8_t)~MODULE_FLAG_MOVING;
    return true;
}

void module_mark_persisted(volatile module_state_t *state)
{
    if (!module_is_moving(state)) {
        state->flags &= (uint8_t)~MODULE_FLAG_PERSIST_PENDING;
    }
}

bool module_is_calibrated(const volatile module_state_t *state)
{
    return flag_is_set(state, MODULE_FLAG_CALIBRATED);
}

bool module_is_moving(const volatile module_state_t *state)
{
    return flag_is_set(state, MODULE_FLAG_MOVING);
}

bool module_needs_persist(const volatile module_state_t *state)
{
    return flag_is_set(state, MODULE_FLAG_PERSIST_PENDING);
}

uint16_t module_half_steps_to_next_position(
    uint8_t current_position,
    uint16_t half_steps_per_revolution
)
{
    const uint8_t position = current_position & MODULE_STATUS_POSITION_MASK;
    const uint8_t next_position = position + 1u;
    const uint16_t base_steps =
        half_steps_per_revolution / MODULE_POSITION_COUNT;
    const uint8_t remainder =
        half_steps_per_revolution % MODULE_POSITION_COUNT;
    const uint16_t current_extra =
        (uint16_t)remainder * position / MODULE_POSITION_COUNT;
    const uint16_t next_extra =
        (uint16_t)remainder * next_position / MODULE_POSITION_COUNT;

    return base_steps + next_extra - current_extra;
}

bool module_sequence_is_newer(uint8_t candidate, uint8_t reference)
{
    const uint8_t distance = candidate - reference;

    return distance != 0u && distance < 128u;
}
