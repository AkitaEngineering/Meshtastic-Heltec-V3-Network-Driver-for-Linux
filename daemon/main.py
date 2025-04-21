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
import configparser
import socket
import json
from enum import Enum

# --- Configuration ---
CONFIG_FILE = 'config.ini'
DEFAULT_SERIAL_PORT = '/dev/ttyACM0'
DEFAULT_SERIAL_BAUDRATE = 115200
DEFAULT_TUN_NAME = 'meshtun0'
DEFAULT_TUN_ADDR = '10.0.0.1'
DEFAULT_TUN_NETMASK = '255.255.255.0'
DEFAULT_MTU = 1500
NODE_ID_PREFIX = 'msh'

# --- Meshtastic Protocol Definition (Conceptual - Needs Actual Specification) ---
PREAMBLE = b'!'
PACKET_START = b'<'
PACKET_END = b'>'
ADDRESS_SEPARATOR = b':'
PAYLOAD_SEPARATOR = b'|'

class PacketType(Enum):
    DATA = 'DATA'
    NODE_INFO = 'NODE_INFO'
    TEXT = 'TEXT'
    # Add more packet types as needed

def encode_meshtastic_packet(payload_data, destination_node=None, source_node=None, packet_type=PacketType.DATA, hop_limit=3):
    """Encodes data into a more structured Meshtastic-like packet."""
    packet = PREAMBLE + PACKET_START
    if destination_node:
        packet += destination_node.encode() + ADDRESS_SEPARATOR
    if source_node:
        packet += source_node.encode() + ADDRESS_SEPARATOR
    packet += packet_type.value.encode() + PAYLOAD_SEPARATOR
    header = {'hop': 0, 'limit': hop_limit}
    packet += json.dumps(header).encode() + PAYLOAD_SEPARATOR
    if isinstance(payload_data, dict):
        packet += json.dumps(payload_data).encode()
    elif isinstance(payload_data, bytes):
        packet += payload_data
    else:
        packet += str(payload_data).encode()
    packet += PACKET_END
    return packet

def decode_meshtastic_packet(data):
    """Decodes a more structured Meshtastic-like packet."""
    if not data.startswith(PREAMBLE + PACKET_START) or not data.endswith(PACKET_END):
        return None
    data = data[len(PREAMBLE) + len(PACKET_START):-len(PACKET_END)]
    parts = data.split(PAYLOAD_SEPARATOR, 2)
    if len(parts) != 3:
        return None

    address_type = parts[0].split(ADDRESS_SEPARATOR)
    destination_node = address_type[0] if len(address_type) > 0 and address_type[0] else None
    source_node = address_type[1] if len(address_type) > 1 and address_type[1] else None
    packet_type_str = address_type[-1] if address_type else PacketType.DATA.value

    header_json = parts[1]
    payload = parts[2]

    try:
        header = json.loads(header_json.decode())
        packet_type = PacketType(packet_type_str)
        return source_node, destination_node, packet_type, payload
    except (json.JSONDecodeError, ValueError):
        logging.warning(f"Error decoding packet header or type: {data}")
        return None

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
        self.discovery_interval = self.config.getint('discovery', 'interval', fallback=60) # seconds

        self.tun = None
        self.serial = None
        self.node_table = {}  # Mapping of Meshtastic node IDs to IP addresses
        self.lock = threading.Lock()
        self.running = True

    def load_node_mapping(self):
        """Loads static node ID to IP mapping from the config."""
        if self.config.has_section('node_mapping'):
            for node_id, ip_address in self.config.items('node_mapping'):
                with self.lock:
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
            # Simple heuristic based on IP suffix (not reliable)
            parts = ip_address.split('.')
            if len(parts) == 4:
                suffix_hex = hex(int(parts[-1]))[2:].zfill(2)
                new_node_id = f"{NODE_ID_PREFIX}-{suffix_hex}"
                if new_node_id not in self.node_table:
                    self.node_table[new_node_id] = ip_address
                    logging.warning(f"Dynamically mapped IP {ip_address} to node ID {new_node_id}")
                    return new_node_id
            return None

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

    def send_node_info_request(self):
        """Sends a broadcast request for node information (conceptual)."""
        payload = {"request": "node_info"}
        packet = encode_meshtastic_packet(payload, packet_type=PacketType.NODE_INFO)
        try:
            if self.serial and self.serial.is_open:
                self.serial.write(packet)
                logging.debug(f"Sent Node Info Request: {packet}")
        except serial.SerialException as e:
            logging.error(f"Serial write error: {e}")

    def handle_node_info(self, source_node, payload_str):
        """Handles received node information."""
        try:
            payload = json.loads(payload_str.decode())
            if 'node_id' in payload and 'ip_address' in payload:
                with self.lock:
                    self.node_table[payload['node_id']] = payload['ip_address']
                logging.info(f"Received Node Info: {payload['node_id']} -> {payload['ip_address']}")
        except json.JSONDecodeError:
            logging.warning(f"Error decoding node info payload from {source_node}: {payload_str}")

    def read_from_tun(self):
        """Reads packets from the TUN interface and sends them over serial."""
        while self.running and self.tun:
            try:
                packet = self.tun.read(self.tun.mtu)
                if packet:
                    logging.debug(f"Read {len(packet)} bytes from TUN.")
                    # Basic IP address extraction
                    dest_ip_bytes = packet[16:20] if len(packet) >= 20 else None
                    if dest_ip_bytes:
                        dest_ip = socket.inet_ntoa(dest_ip_bytes)
                        dest_node = self.resolve_node_id_to_ip(dest_ip)
                        if dest_node:
                            meshtastic_payload = packet
                            meshtastic_packet = encode_meshtastic_packet(meshtastic_payload, destination_node=dest_node, source_node=self.node_id)
                            try:
                                self.serial.write(meshtastic_packet)
                                logging.debug(f"Wrote {len(meshtastic_packet)} bytes to serial (dest: {dest_node}).")
                            except serial.SerialException as e:
                                logging.error(f"Serial write error: {e}")
                                self.running = False
                                break
                        else:
                            logging.warning(f"No Meshtastic node found for IP {dest_ip}. Dropping packet.")
                    else:
                        logging.warning("Could not extract destination IP from TUN packet.")
                time.sleep(0.01)
            except pytun.TunError as e:
                logging.error(f"TUN read error: {e}")
                self.running = False
                break

    def read_from_serial(self):
        """Reads data from the serial port and processes Meshtastic packets."""
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
                            source_node, _, packet_type, payload_bytes = decoded
                            logging.debug(f"Received Meshtastic packet from {source_node} ({packet_type.value}): {payload_bytes.hex()}")

                            if packet_type == PacketType.NODE_INFO:
                                self.handle_node_info(source_node, payload_bytes)
                            elif packet_type == PacketType.DATA:
                                # Try to inject the raw payload (assuming it's an IP packet)
                                source_ip = self.resolve_node_id_to_ip(source_node)
                                if source_ip:
                                    try:
                                        self.tun.write(payload_bytes)
                                        logging.debug(f"Injected {len(payload_bytes)} bytes into TUN from {source_node} ({
                                            source_ip}).")
                                    except pytun.TunError as e:
                                        logging.error(f"TUN write error: {e}")
                                        self.running = False
                                        break
                                else:
                                    logging.warning(f"No IP address known for Meshtastic node {source_node}.")
                            elif packet_type == PacketType.TEXT:
                                try:
                                    text = payload_bytes.decode('utf-8', errors='ignore')
                                    logging.info(f"Received text from {source_node}: {text}")
                                    # Optionally handle text messages (e.g., display, forward)
                                except UnicodeDecodeError:
                                    logging.warning(f"Could not decode text message from {source_node}.")
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
        discovery_thread = threading.Thread(target=self._periodic_discovery, daemon=True)

        tun_thread.start()
        serial_thread.start()
        discovery_thread.start()

        logging.info("Meshtastic Daemon started.")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Exiting...")
            self.running = False
        finally:
            self.running = False
            if self.tun:
                os.system(f'ip link set dev {self.tun_name} down')
                logging.info(f"TUN interface {self.tun_name} down.")
                self.tun.close()
            if self.serial and self.serial.is_open:
                self.serial.close()
                logging.info(f"Serial port {self.serial_port} closed.")
            tun_thread.join(timeout=1)
            serial_thread.join(timeout=1)
            discovery_thread.join(timeout=1)
            logging.info("Meshtastic Daemon stopped.")

    def _periodic_discovery(self):
        """Periodically sends node discovery requests."""
        while self.running:
            self.send_node_info_request()
            time.sleep(self.discovery_interval)

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
        config['discovery'] = {'interval': 60}
        # Add a sample static node mapping
        config['node_mapping'] = {'my_other_node': '10.0.0.2'}
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)
        logging.info(f"Default configuration written to {CONFIG_FILE}. Please review and adjust {CONFIG_FILE}.")
        exit(0)

    daemon = MeshtasticDaemon(CONFIG_FILE)
    daemon.run()
