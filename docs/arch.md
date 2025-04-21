# Architecture

The Meshtastic Network Driver for Linux consists of two main components:

1.  **Kernel Module (`kernel/heltec.c`):** This module primarily focuses on identifying the Heltec V3 device when connected via USB and associating it with a serial port interface provided by the kernel (e.g., `cdc_acm`). It doesn't handle the Meshtastic protocol itself.

2.  **User-Space Daemon (`daemon/main.py`):** This Python application runs in user space and performs the core bridging functionality:
    - It opens the serial port associated with the Heltec V3.
    - It creates and configures a TUN (Tunnel) virtual network interface.
    - It implements a (conceptual) Meshtastic protocol encoding and decoding scheme.
    - It reads raw data from the serial port, attempts to decode Meshtastic packets, and injects the payload into the TUN interface (assuming it's an IP packet).
    - It reads packets from the TUN interface, encapsulates them into (conceptual) Meshtastic packets, and sends them over the serial port.
    - It includes basic node discovery and IP address mapping.
    - It uses a configuration file (`config.ini`) for settings.

The kernel module facilitates the physical connection to the hardware, while the user-space daemon handles the higher-level protocol translation and network interface management.
