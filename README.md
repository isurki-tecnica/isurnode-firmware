# The ISURNODE Firmware Project
=====================================

This is the custom MicroPython firmware (based on v1.25.0) for the ISURKI ISURNODE IoT Datalogger (STM32).
It aims to provide a reliable and optimized firmware for data logging applications, leveraging the flexibility of MicroPython.

WARNING: This project is derived from MicroPython v1.25.0 and includes custom modifications. While effort is made to maintain stability, it is subject to changes and may differ from upstream MicroPython.

## Build Environment
-----------------
The recommended build environment is **Ubuntu Linux**.

For Windows users, native compilation is complex and **not recommended**. Please use the **Windows Subsystem for Linux (WSL)** and follow the Ubuntu instructions below for a more stable and straightforward setup.

## Build Instructions (Ubuntu / WSL)
---------------------------------

### Step 1: Install System Dependencies

Open your Ubuntu terminal and install all required packages. This includes the standard build tools and the specific **ARM Cross-Compiler** required for STM32.

```bash
sudo apt update && sudo apt upgrade -y

# Install core build tools, Python, and Git
sudo apt-get install build-essential libffi-dev git pkg-config python3 python3-pip

# Install the ARM Cross-Compiler Toolchain (CRITICAL for STM32)
sudo apt install -y gcc-arm-none-eabi binutils-arm-none-eabi

# Install DFU tool for flashing
sudo apt install -y dfu-util
Step 2: Clone This Repository
Clone this private firmware repository to your system:

Bash

cd ~
git clone [https://github.com/isurki-tecnica/isurnode-firmware.git](https://github.com/isurki-tecnica/isurnode-firmware.git)

# Navigate into the repo
cd isurnode-firmware

# Switch to our working branch (if not already on 'main')
git checkout main
Step 3: Compile the Firmware
Finally, navigate to the stm32 port directory within the cloned repository and run the build commands:

Bash

# Navigate to the STM32 port
cd ports/stm32

# Clean any previous builds (optional, but recommended)
make BOARD=ISURNODE clean

# Download MicroPython submodules (including stm32lib)
make submodules

# Start the build process
make BOARD=ISURNODE
Firmware File Location
The compiled firmware file will be generated in the following directory, accessible from both your WSL environment and Windows:

ports/stm32/build-ISURNODE/firmware.bin

Step 4: Flashing & Filesystem Setup
Flashing the Firmware (J-Link)
Connect a J-Link programmer to the JTAG port on the ISURNODE.

Open the STM32CubeProgrammer software.

Connect to the device using the J-Link.

Flash the compiled firmware.bin file to the address 0x08000000.

Creating the Filesystem (Lfs1-mk.py)
After the first flash, the internal filesystem must be created.

Connect to the ISURNODE's REPL (e.g., using a serial terminal in STM32CubeProgrammer, Thonny, or rshell).

Paste the following Python code into the REPL and execute it. This will format the flash and create a main.py file.

Python

import pyb, os
try:
    os.umount('/flash')
except Exception: 
    pass
print('Creating new filesystem')
os.VfsLfs1.mkfs(pyb.Flash(start=0))
os.mount(pyb.Flash(start=0), '/flash')
os.chdir('/flash')
f=open('main.py', 'w')
f.write('# main.py -- put your code here!\r\n')
f.close()
print(os.statvfs('/flash'))
print(os.listdir())
f=open('main.py')
print(f.read())
f.close()
Step 5: Application Code (app/)
This repository also contains the /app folder.

IMPORTANT: The contents of this folder (main.py, config/, etc.) are NOT compiled into the firmware. These files represent the Python application logic and must be uploaded manually to the STM32's filesystem (e.g., using Thonny or rshell) after flashing the firmware and creating the filesystem. This allows for flexible updates to the application logic without recompiling the entire firmware.