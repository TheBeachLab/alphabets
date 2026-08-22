# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
TARGET := alphabets-v2-module
MCU ?= attiny44a
F_CPU ?= 8000000UL

AVR_CC ?= avr-gcc
AVR_OBJCOPY ?= avr-objcopy
AVR_SIZE ?= avr-size
AVRDUDE ?= avrdude
HOST_CC ?= cc
PROGRAMMER ?= usbtiny
AVRDUDE_FLAGS ?=

BUILD_DIR := build
SOURCES := module.c protocol_core.c
OBJECTS := $(SOURCES:%.c=$(BUILD_DIR)/%.o)
ELF := $(BUILD_DIR)/$(TARGET).elf
HEX := $(BUILD_DIR)/$(TARGET).hex
HOST_TEST := $(BUILD_DIR)/test-protocol-core

CPPFLAGS += -DF_CPU=$(F_CPU)
CFLAGS += -std=gnu11 -Wall -Wextra -Werror -Os -mmcu=$(MCU) \
	-ffunction-sections -fdata-sections
LDFLAGS += -mmcu=$(MCU) -Wl,--gc-sections

.PHONY: all size test check flash clean

all: $(HEX) size

$(BUILD_DIR):
	mkdir -p $@

$(BUILD_DIR)/%.o: %.c protocol_core.h | $(BUILD_DIR)
	$(AVR_CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(ELF): $(OBJECTS)
	$(AVR_CC) $(LDFLAGS) $^ -o $@

$(HEX): $(ELF)
	$(AVR_OBJCOPY) -O ihex -R .eeprom $< $@

size: $(ELF)
	$(AVR_SIZE) -C --mcu=$(MCU) $<

$(HOST_TEST): protocol_core.c protocol_core.h test_protocol_core.c | $(BUILD_DIR)
	$(HOST_CC) -std=c11 -Wall -Wextra -Werror -O2 \
		protocol_core.c test_protocol_core.c -o $@

test: $(HOST_TEST)
	$(HOST_TEST)

check: test all

flash: $(HEX)
	$(AVRDUDE) -p t44 -c $(PROGRAMMER) $(AVRDUDE_FLAGS) -U flash:w:$<:i

clean:
	rm -rf $(BUILD_DIR)
