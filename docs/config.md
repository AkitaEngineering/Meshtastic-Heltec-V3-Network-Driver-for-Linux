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
  ```

# Meshtastic Protocol Implementation Notes

The `main.py` daemon includes a basic, conceptual implementation of the Meshtastic protocol. **This implementation is simplified and needs to be fully aligned with the actual Meshtastic serial protocol specification.**

**Packet Structure (Conceptual):**

Packets are framed with `!` as a preamble, `<` as the start delimiter, and `>` as the end delimiter. Fields within the packet are separated by `:`. The payload is separated from the header by `|`. !&lt;destination_node>:&lt;source_node>:&lt;packet_type>|&lt;header_json>|&lt;payload>
- `destination_node`: The target Meshtastic node ID (optional for broadcasts).
- `source_node`: The originating Meshtastic node ID.
- `packet_type`: A string indicating the type of packet (e.g., `DATA`, `NODE_INFO`, `TEXT`).
- `header_json`: A JSON string containing metadata about the packet (e.g., hop count).
- `payload`: The actual data being transmitted.

**Node Discovery (Conceptual):**

The daemon periodically sends out `NODE_INFO` requests. Other nodes (including real Meshtastic devices if they respond to such requests in the future) might respond with their node ID and a suggested IP address.

**Important:** This is a simplified representation. The actual Meshtastic protocol is likely more complex and may include different framing, addressing schemes, and control messages. A thorough understanding of the official Meshtastic serial protocol is essential for a complete implementation.

