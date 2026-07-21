CC ?= clang
BUILD_DIR := build
FIRMWARE_DIR := firmware/stm32f0
TEST_DIR := tests

CPPFLAGS := -I$(FIRMWARE_DIR) -I$(TEST_DIR)/stubs
COMMON_CFLAGS := -std=c11 -Wall -Wextra -Wpedantic -Wconversion -Wshadow
SANITIZER_FLAGS := -fsanitize=undefined -fno-sanitize-recover=all
TEST_CFLAGS := $(COMMON_CFLAGS) -O1 -g $(SANITIZER_FLAGS)
STRICT_CFLAGS := $(COMMON_CFLAGS) -Werror -O2

.PHONY: all characterize test test-font test-scan warnings analyze clean

all: test

$(BUILD_DIR):
	mkdir -p $@

$(BUILD_DIR)/test_vfd_font: $(TEST_DIR)/test_vfd_font.c \
		$(FIRMWARE_DIR)/GT20L_Font.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(TEST_CFLAGS) $^ -o $@

$(BUILD_DIR)/test_vfd_scan: $(TEST_DIR)/test_vfd_scan.c \
		$(FIRMWARE_DIR)/vfd_scan.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(TEST_CFLAGS) $^ -o $@

characterize: $(BUILD_DIR)/test_vfd_font
	./$(BUILD_DIR)/test_vfd_font valid

test-font: $(BUILD_DIR)/test_vfd_font
	./$(BUILD_DIR)/test_vfd_font

test-scan: $(BUILD_DIR)/test_vfd_scan
	./$(BUILD_DIR)/test_vfd_scan

test: test-font test-scan

warnings:
	$(CC) $(CPPFLAGS) $(STRICT_CFLAGS) -fsyntax-only \
		$(FIRMWARE_DIR)/GT20L_Font.c $(FIRMWARE_DIR)/vfd_scan.c

analyze:
	$(CC) $(CPPFLAGS) $(COMMON_CFLAGS) --analyze \
		$(FIRMWARE_DIR)/GT20L_Font.c $(FIRMWARE_DIR)/vfd_scan.c

clean:
	rm -rf $(BUILD_DIR)
