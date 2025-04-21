# Configuration (`config.ini`)

The `config.ini` file in the `daemon/` directory controls the behavior of the Meshtastic daemon.

**`[serial]` Section:**
- `port`: The path to the serial port connected to the Heltec V3 (e.g., `/dev/ttyACM0`, `/dev/ttyUSB0`). **This is crucial and must be correct.**
- `baudrate`: The baud rate used for serial communication with the Heltec V3 (default: 115200).

**`[tun]` Section:**
- `name`: The name of the TUN virtual network interface to create (default: `meshtun0`).
- `address`: The IP address to assign to the TUN interface (default: `10.0.0.1`).
- `netmask`: The netmask for the TUN interface (default: `255.255.255.0`).
- `mtu`: The Maximum Transmission Unit for the TUN interface (default: 1500).

**`[meshtastic]` Section:**
- `node_id`: A unique identifier for this virtual Meshtastic node (default: generated randomly).

**`[discovery]` Section:**
- `interval`: The interval (in seconds) at which the daemon will send out node discovery requests (default: 60).

**`[node_mapping]` Section (Optional):**
- You can define static mappings between Meshtastic node IDs and IP addresses here. Each line should be in the format `node_id = ip_address`. For example:
  ```ini
  [node_mapping]
  my_other_node = 10.0.0.2
  another_node = 10.0.0.3
