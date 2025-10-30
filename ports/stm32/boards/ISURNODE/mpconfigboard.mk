MCU_SERIES = l4
CMSIS_MCU = STM32L431xx
AF_FILE = boards/stm32l431_af.csv
LD_FILES = boards/stm32l431.ld boards/common_basic.ld
OPENOCD_CONFIG = boards/openocd_stm32l4.cfg

# MicroPython settings
MICROPY_VFS_FAT = 0
MICROPY_VFS_LFS1 = 1
MICROPY_HW_ENABLE_ISR_UART_FLASH_FUNCS_IN_RAM = 1

# LTO reduces final binary size, may be slower to build depending on gcc version and hardware
LTO = 1

# --- CONFIGURACIÓN DE MÓDULOS CONGELADOS ---
# 1. Apunta al directorio que contiene tus carpetas 'lib' y 'modules'
FROZEN_MANIFEST ?= $(BOARD_DIR)/manifest.py

