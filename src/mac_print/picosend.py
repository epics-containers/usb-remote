"""
A script to send the MAC address of the host machine to a connected Raspberry
Pi Pico device via USB serial communication. The script waits for the device to
be connected and sends the message once connected.
"""

from time import sleep

import pyudev
import serial
import serial.tools.list_ports

pico_vid = 0x2E8A  # Raspberry Pi Pico Vendor ID
pico_pid = 0x0005  # Pico with MicroPython firmware


def get_host_name() -> str:
    import socket

    hostname = socket.gethostname()
    return hostname


def get_mac_address() -> str:
    import os

    # Get list of network interfaces
    net_path = "/sys/class/net"
    interfaces = [
        i for i in os.listdir(net_path) if i != "lo" and not i.startswith("docker")
    ]  # Exclude loopback and docker

    # Sort to ensure consistent ordering
    interfaces.sort()

    if not interfaces:
        return "00:00:00:00:00:00"

    # Get MAC address of first interface
    first_nic = interfaces[0]
    mac_file = os.path.join(net_path, first_nic, "address")

    try:
        with open(mac_file) as f:
            mac_str = f.read().strip().upper()
        return mac_str
    except OSError:
        return "00:00:00:00:00:00"


def check_for_pico():
    # Check if a pico is connected
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.vid == pico_vid and port.pid == pico_pid:
            print("Pico found at:", port.device)
            return port.device
    return None


def wait_for_device():
    """
    Wait for a Raspberry Pi Pico device to be connected using udev events.
    Returns the serial port path when found.
    """

    # Set up udev monitoring
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem="tty")

    while True:
        print("Waiting for device to be connected...")

        # Wait for device connection events
        for action, device in monitor:
            if action == "add":
                print(f"Device added: {device.device_node}")
                device = check_for_pico()
                if device is not None:
                    return device


def send_message(port_path: str, message: str):
    try:
        # Open serial connection
        ser = serial.Serial(port_path, baudrate=115200, timeout=1)

        # Clear any pending data
        ser.reset_output_buffer()

        # Send the message
        ser.write(message.encode())
        print(f"Sent message: {message}")

        ser.close()

    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")


def main():
    """
    A function that waits for a raspi pico device 2e8a:0005 to be connected via USB
    and sends the current MAC address to it via the serial port.
    """
    msg = f"MAC address:\n{get_mac_address()}\n"
    msg += "---------------\n"
    msg += f"host name:\n{get_host_name()}\n"

    port_path = check_for_pico()
    if port_path is not None:
        sleep(1)  # wait for the device to be ready
        print("sending to currently connected device:", port_path)
        send_message(port_path, msg)

    while True:
        port_path = wait_for_device()
        send_message(port_path, msg)


if __name__ == "__main__":
    main()
