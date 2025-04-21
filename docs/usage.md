# Usage

**Prerequisites:**
- A Linux system with kernel headers installed.
- Python 3 with `pyserial` and `pytun` libraries installed (`pip install -r daemon/requirements.txt`).
- The `iproute2` package (usually pre-installed on most Linux distributions).

**Installation:**

1.  **Kernel Module:**
    - Navigate to the `kernel/` directory.
    - Run `make` to build the `heltec.ko` file.
    - Load the kernel module (you might need to use `sudo`): `sudo insmod heltec.ko`
    - To load the module automatically on boot, you might need to add it to your kernel modules configuration (distribution-specific).

2.  **User-Space Daemon:**
    - Navigate to the `daemon/` directory.
    - Ensure the `main.py` file is executable: `chmod +x main.py`

**Configuration:**

- A `config.ini` file will be created in the `daemon/` directory if it doesn't exist.
- Edit this file to configure the serial port, baud rate, TUN interface IP address, and other settings. **Pay close attention to the `[serial]` section and ensure the `port` setting matches the serial device assigned to your Heltec V3 (check `dmesg` output after plugging it in).**

**Running:**

- Run the user-space daemon with root privileges (required for creating the TUN interface): `sudo ./daemon/main.py`

**Verification:**

- After running the daemon, a new network interface (e.g., `meshtun0`) should appear in your network interfaces list (`ip a` or `ifconfig`).
- You should see logging output in your terminal indicating the daemon's activity.

**Stopping:**

- Press `Ctrl+C` in the terminal where the daemon is running to stop it.
- To unload the kernel module: `sudo rmmod heltec`
- You might need to manually bring down the TUN interface: `sudo ip link set dev meshtun0 down`
