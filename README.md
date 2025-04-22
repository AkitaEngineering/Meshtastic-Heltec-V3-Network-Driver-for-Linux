# Meshtastic Heltec V3 Network Driver for Linux

[![WIP - Conceptual Project](https://img.shields.io/badge/Status-WIP%20Conceptual-orange.svg)](https://github.com/akita-engineering/Meshtastic-Heltec-V3-Network-Driver-for-Linux)
[![Akita Engineering](https://img.shields.io/badge/Organization-Akita%20Engineering-blue.svg)](https://www.akitaengineering.com)

This project, initiated by Akita Engineering (www.akitaengineering.com), is a **Work In Progress (WIP) and conceptual in nature**. It aims to create a Linux driver that allows a Heltec V3 device running Meshtastic firmware to act as a network interface. This would enable Linux applications to communicate over the Meshtastic network using standard network protocols (via a TUN virtual interface).

**Please note:** This project is currently in an early, conceptual stage and may not be fully functional or production-ready. Contributions and collaboration are welcome to help bring this concept to fruition.

## Overview

The goal is to bridge the gap between the Meshtastic radio capabilities of the Heltec V3 and the standard Linux networking stack. This driver intends to:

- Detect a Heltec V3 device connected via USB.
- Associate it with a serial port interface.
- Create a virtual TUN (Tunnel) network interface on the Linux system.
- Implement the Meshtastic protocol in user space to handle communication over the serial port.
- Translate network packets from the TUN interface into Meshtastic packets and vice versa.

## Project Structure

- `kernel/`: Contains the Linux kernel module for identifying the Heltec V3.
- `daemon/`: Contains the user-space Python daemon for handling the Meshtastic protocol and the TUN interface.
- `docs/`: Contains documentation about the project's architecture, usage, configuration, and conceptual protocol implementation.
- `examples/`: (Future) Example scripts and configurations.
- `LICENSE`: Specifies the project's license.
- `README.md`: This file, providing an overview of the project.
- `CONTRIBUTING.md`: Guidelines for contributors.

## Getting Started

As this is a WIP and conceptual project, the following steps provide a general outline for those interested in exploring or contributing:

1.  **Prerequisites:**
    - A Linux system with kernel headers installed.
    - Python 3 with `pyserial` and `pytun` libraries installed (`pip install -r daemon/requirements.txt`).
    - The `iproute2` package (usually pre-installed on most Linux distributions).
    - A Heltec V3 device flashed with Meshtastic firmware.

2.  **Explore the Code:**
    - Review the code in the `kernel/` and `daemon/` directories to understand the current conceptual implementation.
    - Read the documentation in the `docs/` directory for more details on the architecture and intended functionality.

3.  **Build and Install (Conceptual):**
    - **Kernel Module:** Navigate to the `kernel/` directory and run `make`. You can attempt to load the module using `sudo insmod heltec.ko`.
    - **User-Space Daemon:** Navigate to the `daemon/` directory and ensure `main.py` is executable (`chmod +x main.py`). You can attempt to run it with `sudo ./main.py`.

4.  **Configuration:**
    - Examine the `config.ini` file in the `daemon/` directory for configuration options. **Ensure the serial port is correctly identified for your Heltec V3.**

## Contributions Welcome!

Akita Engineering encourages contributions from the community to help advance this conceptual project. If you have expertise in any of the following areas, we would love to hear from you:

- **Meshtastic Protocol:** Deep understanding of the serial protocol and its intricacies.
- **Linux Kernel Development:** Experience in writing and debugging kernel modules.
- **Python Networking:** Skills in developing network applications, especially with TUN/TAP interfaces.
- **Embedded Systems:** Knowledge of the Heltec V3 hardware and Meshtastic firmware.
- **Testing and Validation:** Expertise in creating test cases and ensuring the reliability of the driver.
- **Documentation:** Helping to improve and expand the project's documentation.

Please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines on how to contribute.

## License

GNU General Public License v3.0 (See `LICENSE` file)

## Contact

For inquiries or to express interest in contributing, please visit [www.akitaengineering.com](https://www.akitaengineering.com) or contact us through the website.

**Let's build this together!**
