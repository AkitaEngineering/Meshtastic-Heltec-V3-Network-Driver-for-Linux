# Meshtastic Daemon

This Python daemon bridges a Meshtastic network (connected via serial) to a virtual TUN network interface on Linux.

**Dependencies:**
- pyserial
- pytun

Install them using: `pip install -r requirements.txt`

**Configuration:**
Configuration is read from `config.ini`. See the default configuration for available options.

**Running:**
Run the daemon with root privileges: `sudo ./main.py`
