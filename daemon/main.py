#!/usr/bin/env python3

import serial
import pytun
import struct
import fcntl
import os
import time
import select
import logging
import threading
import configparser  # For configuration file
import socket       # For potential network discovery
import json         # For potential structured data in Meshtastic payloads

# --- Configuration ---
CONFIG_FILE = 'config.ini'
DEFAULT_SERIAL_PORT = '/dev/ttyACM0'
DEFAULT_SERIAL_BAUDRATE = 115200
DEFAULT_TUN_NAME = 'meshtun0'
DEFAULT_TUN_ADDR = '10.0.0.1'
DEFAULT_TUN_NETMASK = '255.255.255.0'
DEFAULT_MTU = 1500
NODE_ID_PREFIX = 'msh'  # Prefix for our virtual Meshtastic node ID

# --- Meshtastic Protocol Implementation (More Detailed - Still Conceptual) ---
PREAMBLE = b'!'
PACKET_START = b'<'
PACKET_END = b'>'
ADDRESS_SEPARATOR = b':'
PAYLOAD_SEPARATOR = b'|'  # Separator within the payload for structured data

def encode_meshtastic_packet(payload_data, destination_node=None, source_node=None, packet_type='DATA'):
    """
    Encodes data into a more structured Meshtastic-like packet.
    """
    packet = PREAMBLE + PACKET_START
    if destination_node:
        packet += destination_node.encode() + ADDRESS_SEPARATOR
    if source_node:
        packet += source_node.encode() + ADDRESS_SEPARATOR
    packet += packet_type.encode() + PAYLOAD_SEPARATOR
    if isinstance(payload_data, dict):
        packet += json.dumps(payload_data).encode()
    elif isinstance(payload_data, bytes):
        packet += payload_data
    else:
        packet += str(payload_data).encode()
    packet += PACKET_END
    return packet

def decode_meshtastic_packet(data):
    """
    Decodes a more structured Meshtastic-like packet.
    Returns (source_node, destination_node, packet_type, payload) or None if invalid.
    """
    if not data.startswith(PREAMBLE + PACKET_START) or not data.endswith(PACKET_END):
        return None
    data = data[len(PREAMBLE) + len(PACKET_START):-len(PACKET_END)]
    parts = data.split(PAYLOAD_SEPARATOR, 1)
    if len(parts) != 2:
        return None
    header_str = parts[0]
    payload = parts[1]

    address_parts = header_str.split(ADDRESS_SEPARATOR)
    destination_node = address_parts[0] if len(address_parts) > 0 and address_parts[0] else None
    source_node = address_parts[1] if len(address_parts) > 1 and address_parts[1] else None
    packet_type = address_parts[-1] if address_parts else 'DATA' # Assume DATA if no type

    return source_node, destination_node, packet_type.decode(), payload

class MeshtasticDaemon:
    def __init__(self, config_file):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        self.serial_port = self.config.get('serial', 'port', fallback=DEFAULT_SERIAL_PORT)
        self.serial_baudrate = self.config.getint('serial', 'baudrate', fallback=DEFAULT_SERIAL_BAUDRATE)
        self.tun_name = self.config.get('tun', 'name', fallback=DEFAULT_TUN_NAME)
        self.tun_addr = self.config.get('tun', 'address', fallback=DEFAULT_TUN_ADDR)
        self.tun_netmask = self.config.get('tun', 'netmask', fallback=DEFAULT_TUN_NETMASK)
        self.mtu = self.config.getint('tun', 'mtu', fallback=DEFAULT_MTU)
        self.node_id = self.config.get('meshtastic', 'node_id', fallback=f"{NODE_ID_PREFIX}-{os.urandom(4).hex()}")

        self.tun = None
        self.serial = None
        self.node_table = {}  # Mapping of Meshtastic node IDs to IP addresses (basic)
        self.lock = threading.Lock()
        self.running = True

    def load_node_mapping(self):
        """Loads a static node ID to IP mapping from the config."""
        if self.config.has_section('node_mapping'):
            for node_id, ip_address in self.config.items('node_mapping'):
                self.node_table[node_id] = ip_address
                logging.info(f"Loaded static node mapping: {node_id} -> {ip_address}")

    def resolve_node_id_to_ip(self, node_id):
        """Resolves a Meshtastic node ID to an IP address."""
        with self.lock:
            return self.node_table.get(node_id)

    def map_ip_to_node_id(self, ip_address):
        """Maps an IP address to a Meshtastic node ID (for our virtual network)."""
        with self.lock:
            for node_id, ip in self.node_table.items():
                if ip == ip_address:
                    return node_id
            # Basic dynamic assignment (not robust for a real network)
            new_node_id = f"{NODE_ID_PREFIX}-{ip_address.split('.')[-1]}"
            self.node_table[new_node_id] = ip_address
            logging.warning(f"Dynamically assigned node ID {new_node_id} to IP {ip_address}")
            return new_node_id

    def create_tun_interface(self):
        """Creates and configures the TUN interface."""
        try:
            self.tun = pytun.Tun(self.tun_name)
            logging.info(f"TUN interface {self.tun_name} created.")
            os.system(f'ip addr add {self.tun_addr}/{self.tun_netmask.split(".").count("255")} dev {self.tun_name}')
            os.system(f'ip link set dev {self.tun_name} up mtu {self.mtu}')
            logging.info(f"TUN interface {self.tun_name} configured with IP {self.tun_addr}, netmask {self.tun_netmask}, MTU {self.mtu}.")
            return True
        except pytun.TunError as e:
            logging.error(f"Error creating TUN interface: {e}")
            return False

    def open_serial_port(self):
        """Opens the serial port."""
        try:
            self.serial = serial.Serial(self.serial_port, self.serial_baudrate, timeout=1)
            logging.info(f"Serial port {self.serial_port} opened.")
            return True
        except serial.SerialException as e:
            logging.error(f"Error opening serial port {self.serial_port}: {e}")
            return False

    def read_from_tun(self):
        """Reads packets from the TUN interface and sends them over serial."""
        while self.running and self.tun:
            try:
                packet = self.tun.read(self.tun.mtu)
                if packet:
                    logging.debug(f"Read {len(packet)} bytes from TUN.")
                    # Basic IP address extraction (very simplified)
                    dest_ip = socket.inet_ntoa(packet[16:20]) if len(packet) >= 20 else None
                    dest_node = self.resolve_node_id_to_ip(dest_ip) # Try resolving IP to a known node

                    meshtastic_payload = packet
                    meshtastic_packet = encode_meshtastic_packet(meshtastic_payload, destination_node=dest_node, source_node=self.node_id)
                    try:
                        self.serial.write(meshtastic_packet)
                        logging.debug(f"Wrote {len(meshtastic_packet)} bytes to serial.")
                    except serial.SerialException as e:
                        logging.error(f"Serial write error: {e}")
                        self.running = False
                        break
                time.sleep(0.01)
            except pytun.TunError as e:
                logging.error(f"TUN read error: {e}")
                self.running = False
                break

    def read_from_serial(self):
        """Reads data from the serial port and injects valid packets into the TUN interface."""
        buffer = b''
        while self.running and self.serial and self.serial.is_open:
            try:
                data = self.serial.read(self.serial.in_waiting or 1)
                if data:
                    buffer += data
                    while PACKET_END in buffer:
                        end_index = buffer.find(PACKET_END)
                        packet = buffer[:end_index + len(PACKET_END)]
                        buffer = buffer[end_index + len(PACKET_END):]
                        decoded = decode_meshtastic_packet(packet)
                        if decoded:
                            source_node, _, _, payload = decoded
                            logging.debug(f"Decoded Meshtastic packet from {source_node}: Payload={payload.hex()}")
                            # Basic IP address assignment based on source node (very simplified)
                            source_ip = self.resolve_node_id_to_ip(source_node)
                            if not source_ip:
                                # Assign a virtual IP - needs a more robust method
                                parts = source_node.split('-')
                                if len(parts) > 1 and parts[0] == NODE_ID_PREFIX:
                                    last_part = parts[-1]
                                    try:
                                        virtual_ip_suffix = int(last_part, 16) % 254 + 1 # Simple derivation
                                        source_ip = f"10.0.0.{virtual_ip_suffix}"
                                        with self.lock:
                                            self.node_table[source_node] = source_ip
                                            logging.info(f"Mapped node {source_node} to IP {source_ip}")
                                    except ValueError:
                                        logging.warning(f"Could not derive IP for node {source_node}")
                                        continue
                                else:
                                    logging.warning(f"Could not derive IP for node {source_node}")
                                    continue

                            try:
                                # Inject the raw payload (assuming it's an IP packet)
                                self.tun.write(payload)
                                logging.debug(f"Injected {len(payload)} bytes into TUN from {source_node} ({source_ip}).")
                            except pytun.TunError as e:
                                logging.error(f"TUN write error: {e}")
                                self.running = False
                                break
            except serial.SerialException as e:
                logging.error(f"Serial read error: {e}")
                self.running = False
                break
            time.sleep(0.01)

    def run(self):
        """Main execution loop."""
        if not self.create_tun_interface():
            return
        if not self.open_serial_port():
            return

        self.load_node_mapping()

        tun_thread = threading.Thread(target=self.read_from_tun, daemon=True)
        serial_thread = threading.Thread(target=self.read_from_serial, daemon=True)

        tun_thread.start()
        serial_thread.start()

        logging.info("Meshtastic Daemon started.")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Exiting...")
            self.running = False
        finally:
            if self.tun:
                os.system(f'ip link set dev {self.tun_name} down')
                logging.info(f"TUN interface {self.tun_name} down.")
                self.tun.close()
            if self.serial and self.serial.is_open:
                self.serial.close()
                logging.info(f"Serial port {self.serial_port} closed.")

if __name__ == "__main__":
    # Check for root privileges
    if os.geteuid() != 0:
        logging.error("This script requires root privileges to create the TUN interface. Please run with sudo.")
        exit(1)

    # Create default config if it doesn't exist
    if not os.path.exists(CONFIG_FILE):
        config = configparser.ConfigParser()
        config['serial'] = {'port': DEFAULT_SERIAL_PORT, 'baudrate': DEFAULT_SERIAL_BAUDRATE}
        config['tun'] = {'name': DEFAULT_TUN_NAME, 'address': DEFAULT_TUN_ADDR, 'netmask': DEFAULT_TUN_NETMASK, 'mtu': DEFAULT_MTU}
        config['meshtastic'] = {'node_id': f"{NODE_ID_PREFIX}-{os.urandom(4).hex()}"}
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)
        logging.info(f"Default configuration written to {CONFIG_FILE}. Please review and adjust.")
        exit(0)

    daemon = MeshtasticDaemon(CONFIG_FILE)
    daemon.run()
