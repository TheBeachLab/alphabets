// SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
// SPDX-License-Identifier: MIT
#ifndef ALPHABETS_V2_ATTINY1624_PROTOCOL_CORE_H
#define ALPHABETS_V2_ATTINY1624_PROTOCOL_CORE_H

#include <stdbool.h>
#include <stdint.h>

#define MODULE_POSITION_COUNT 64u

#define MODULE_COMMAND_KEEP 0x00u
#define MODULE_COMMAND_POSITION_FIRST 0x01u
#define MODULE_COMMAND_POSITION_LAST 0x40u
#define MODULE_COMMAND_HOME 0x41u

#define MODULE_STATUS_PRESENT 0x80u
#define MODULE_STATUS_READY 0x40u
#define MODULE_STATUS_POSITION_MASK 0x3fu

#define MODULE_FLAG_REFERENCED 0x01u
#define MODULE_FLAG_MOVING 0x02u
#define MODULE_FLAG_PERSIST_PENDING 0x04u
#define MODULE_FLAG_HOMING 0x08u
#define MODULE_FLAG_HOME_RELEASED 0x10u

typedef struct {
    uint8_t current_position;
    uint8_t target_position;
    uint8_t flags;
} module_state_t;

typedef enum {
    MODULE_COMMAND_IGNORED = 0,
    MODULE_COMMAND_ACCEPTED,
    MODULE_COMMAND_START_MOTION,
    MODULE_COMMAND_START_HOME
} module_command_result_t;

void module_state_init(
    volatile module_state_t *state,
    uint8_t stored_position,
    bool stored_position_is_valid
);

uint8_t module_build_status(const volatile module_state_t *state);

module_command_result_t module_apply_command(
    volatile module_state_t *state,
    uint8_t command
);

bool module_reached_next_position(volatile module_state_t *state);
bool module_home_observe(
    volatile module_state_t *state,
    bool home_sensor_active
);
void module_home_failed(volatile module_state_t *state);
void module_mark_persisted(volatile module_state_t *state);

bool module_is_referenced(const volatile module_state_t *state);
bool module_is_moving(const volatile module_state_t *state);
bool module_is_homing(const volatile module_state_t *state);
bool module_needs_persist(const volatile module_state_t *state);

uint16_t module_half_steps_to_next_position(
    uint8_t current_position,
    uint16_t half_steps_per_revolution
);

bool module_sequence_is_newer(uint8_t candidate, uint8_t reference);

#endif
