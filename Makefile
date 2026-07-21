HOST_CC ?= clang
ARM_CC ?= clang
PYTHON ?= python3
TWIN_ARGS ?=

BUILD_DIR := build
FIRMWARE_DIR := firmware/stm32f0
TEST_DIR := tests

HOST_CPPFLAGS := -I$(FIRMWARE_DIR) -I$(TEST_DIR)/stubs
TARGET_CPPFLAGS := -I$(TEST_DIR)/target_stubs -I$(FIRMWARE_DIR)
COMMON_CFLAGS := -std=c11 -Wall -Wextra -Wpedantic -Wconversion -Wshadow \
	-Wcast-qual -Wmissing-prototypes -Wstrict-prototypes
SANITIZER_FLAGS := -fsanitize=undefined -fno-sanitize-recover=all
TEST_CFLAGS := $(COMMON_CFLAGS) -O1 -g $(SANITIZER_FLAGS)
STRICT_CFLAGS := $(COMMON_CFLAGS) -Werror -O2

CORE_SOURCES := \
	$(FIRMWARE_DIR)/GT20L_Font.c \
	$(FIRMWARE_DIR)/font.c \
	$(FIRMWARE_DIR)/vfd_delay.c \
	$(FIRMWARE_DIR)/vfd_framebuffer.c \
	$(FIRMWARE_DIR)/vfd_host_link.c \
	$(FIRMWARE_DIR)/vfd_scan.c
BOARD_SOURCES := \
	$(FIRMWARE_DIR)/main.c \
	$(FIRMWARE_DIR)/stm32f0xx_hal_msp.c \
	$(FIRMWARE_DIR)/stm32f0xx_it.c

.PHONY: all characterize test test-font test-scan test-host-link test-python twin \
	test-delay test-contracts test-dependencies \
	warnings warnings-core warnings-board warnings-tools analyze clean

all: test warnings analyze

$(BUILD_DIR):
	mkdir -p $@

$(BUILD_DIR)/test_vfd_font: $(TEST_DIR)/test_vfd_font.c \
		$(FIRMWARE_DIR)/GT20L_Font.c $(FIRMWARE_DIR)/GT20L_Font.h | $(BUILD_DIR)
	$(HOST_CC) $(HOST_CPPFLAGS) $(TEST_CFLAGS) \
		$(TEST_DIR)/test_vfd_font.c $(FIRMWARE_DIR)/GT20L_Font.c -o $@

$(BUILD_DIR)/test_vfd_scan: $(TEST_DIR)/test_vfd_scan.c \
		$(FIRMWARE_DIR)/vfd_scan.c $(FIRMWARE_DIR)/vfd_scan.h | $(BUILD_DIR)
	$(HOST_CC) $(HOST_CPPFLAGS) $(TEST_CFLAGS) \
		$(TEST_DIR)/test_vfd_scan.c $(FIRMWARE_DIR)/vfd_scan.c -o $@

$(BUILD_DIR)/test_vfd_host_link: $(TEST_DIR)/test_vfd_host_link.c \
		$(FIRMWARE_DIR)/vfd_host_link.c $(FIRMWARE_DIR)/vfd_host_link.h \
		$(FIRMWARE_DIR)/vfd_scan.h | $(BUILD_DIR)
	$(HOST_CC) $(HOST_CPPFLAGS) $(TEST_CFLAGS) \
		$(TEST_DIR)/test_vfd_host_link.c \
		$(FIRMWARE_DIR)/vfd_host_link.c -o $@

$(BUILD_DIR)/vfd_host_link_peer: $(TEST_DIR)/vfd_host_link_peer.c \
		$(FIRMWARE_DIR)/vfd_host_link.c $(FIRMWARE_DIR)/vfd_host_link.h \
		$(FIRMWARE_DIR)/vfd_scan.h | $(BUILD_DIR)
	$(HOST_CC) $(HOST_CPPFLAGS) $(STRICT_CFLAGS) \
		$(TEST_DIR)/vfd_host_link_peer.c \
		$(FIRMWARE_DIR)/vfd_host_link.c -o $@

$(BUILD_DIR)/vfd_pin_twin: tools/vfd_pin_twin.c \
		$(FIRMWARE_DIR)/vfd_scan.c $(FIRMWARE_DIR)/vfd_scan.h | $(BUILD_DIR)
	$(HOST_CC) $(HOST_CPPFLAGS) $(STRICT_CFLAGS) \
		tools/vfd_pin_twin.c $(FIRMWARE_DIR)/vfd_scan.c -o $@

$(BUILD_DIR)/vfd_delay_arm.s: $(FIRMWARE_DIR)/vfd_delay.c \
		$(FIRMWARE_DIR)/vfd_delay.h | $(BUILD_DIR)
	$(ARM_CC) --target=arm-none-eabi -mcpu=cortex-m0 -mthumb -O2 -S \
		-I$(FIRMWARE_DIR) $(FIRMWARE_DIR)/vfd_delay.c -o $@

characterize: $(BUILD_DIR)/test_vfd_font
	./$(BUILD_DIR)/test_vfd_font valid

test-font: $(BUILD_DIR)/test_vfd_font
	./$(BUILD_DIR)/test_vfd_font

test-scan: $(BUILD_DIR)/test_vfd_scan
	./$(BUILD_DIR)/test_vfd_scan

test-host-link: $(BUILD_DIR)/test_vfd_host_link
	./$(BUILD_DIR)/test_vfd_host_link

test-python: $(BUILD_DIR)/vfd_host_link_peer $(BUILD_DIR)/vfd_pin_twin
	PYTHONPATH=src MN12832L_C_PEER=$(CURDIR)/$(BUILD_DIR)/vfd_host_link_peer \
		MN12832L_PIN_TWIN=$(CURDIR)/$(BUILD_DIR)/vfd_pin_twin \
		$(PYTHON) -m unittest discover -s $(TEST_DIR)/python \
		-p 'test_*.py' -v

twin: $(BUILD_DIR)/vfd_pin_twin
	PYTHONPATH=src MN12832L_PIN_TWIN=$(CURDIR)/$(BUILD_DIR)/vfd_pin_twin \
		$(PYTHON) -m mn12832l.twin $(TWIN_ARGS)

test-delay: $(BUILD_DIR)/vfd_delay_arm.s $(TEST_DIR)/check_delay_codegen.py
	$(PYTHON) $(TEST_DIR)/check_delay_codegen.py $(BUILD_DIR)/vfd_delay_arm.s

test-contracts: $(TEST_DIR)/test_firmware_contracts.py $(BOARD_SOURCES)
	$(PYTHON) $(TEST_DIR)/test_firmware_contracts.py

test-dependencies: $(BUILD_DIR)/test_vfd_font $(BUILD_DIR)/test_vfd_scan \
		$(BUILD_DIR)/test_vfd_host_link
	@status=0; $(MAKE) -q -W $(FIRMWARE_DIR)/GT20L_Font.h \
		$(BUILD_DIR)/test_vfd_font || status=$$?; \
		test $$status -eq 1 || { echo "font header dependency check failed"; exit 1; }
	@status=0; $(MAKE) -q -W $(FIRMWARE_DIR)/vfd_scan.h \
		$(BUILD_DIR)/test_vfd_scan || status=$$?; \
		test $$status -eq 1 || { echo "scan header dependency check failed"; exit 1; }
	@status=0; $(MAKE) -q -W $(FIRMWARE_DIR)/vfd_host_link.h \
		$(BUILD_DIR)/test_vfd_host_link || status=$$?; \
		test $$status -eq 1 || { echo "host-link header dependency check failed"; exit 1; }
	@echo "make dependency checks passed"

test: test-font test-scan test-host-link test-python test-delay test-contracts \
	test-dependencies

warnings-core:
	@for source in $(CORE_SOURCES); do \
		echo "[warnings-core] $$source"; \
		$(HOST_CC) $(HOST_CPPFLAGS) $(STRICT_CFLAGS) -fsyntax-only "$$source" || exit; \
	done

warnings-board:
	@for source in $(BOARD_SOURCES); do \
		echo "[warnings-board] $$source"; \
		$(HOST_CC) $(TARGET_CPPFLAGS) $(STRICT_CFLAGS) -fsyntax-only "$$source" || exit; \
	done

warnings-tools: $(BUILD_DIR)/vfd_pin_twin
	$(HOST_CC) $(HOST_CPPFLAGS) $(STRICT_CFLAGS) -fsyntax-only \
		tools/vfd_pin_twin.c

warnings: warnings-core warnings-board warnings-tools

analyze: | $(BUILD_DIR)
	@for source in $(CORE_SOURCES) $(BOARD_SOURCES); do \
		case "$$source" in \
			$(FIRMWARE_DIR)/main.c|$(FIRMWARE_DIR)/stm32f0xx_*.c) includes='$(TARGET_CPPFLAGS)' ;; \
			*) includes='$(HOST_CPPFLAGS)' ;; \
		esac; \
		echo "[analyze] $$source"; \
		$(HOST_CC) $$includes $(COMMON_CFLAGS) --analyze \
			-Xanalyzer -analyzer-output=text "$$source" || exit; \
	done
	@echo "[analyze] tools/vfd_pin_twin.c"
	@$(HOST_CC) $(HOST_CPPFLAGS) $(COMMON_CFLAGS) --analyze \
		-Xanalyzer -analyzer-output=text tools/vfd_pin_twin.c

clean:
	rm -rf $(BUILD_DIR) *.plist
