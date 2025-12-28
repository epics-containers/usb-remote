"""
Module for working with local usbip ports.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from time import sleep

import pyudev

from usb_remote.utility import run_command

logger = logging.getLogger(__name__)

# regex pattern for matching 'usbip port' output https://regex101.com/r/seWBvX/1
re_ports = re.compile(
    r"[pP]ort *(?P<port>\d\d)[\s\S]*?\n *(?P<description>.*)\n[\s\S]*?usbip:\/\/(?P<server>[^:]*):\d*\/(?P<remote_busid>[1-9-.]*)"  # noqa: E501
)


@dataclass
class Port:
    """
    A class for discovering which local usbip ports are in use and detaching from
    those that match the user search criteria.
    """

    port: str  # the local port number
    server: str  # the server ip address
    description: str  # the device description (vendor and product)
    remote_busid: str  # the remote busid of the device

    def __post_init__(self):
        # everything is strings from the regex, convert port to int
        self.port_number = int(self.port)
        # list of local device files (e.g., ["/dev/ttyACM0"])
        self.local_devices = self.get_local_devices()

    def get_local_devices(self) -> list[str]:
        """Find local device files associated with this usbip port.

        Returns:
            List of device file paths (e.g., ["/dev/ttyACM0", "/dev/hidraw0"])
        """
        devices = []

        try:
            context = pyudev.Context()

            # Find all USB devices under vhci_hcd controllers
            # VHCI ports map: port 0 -> devpath "1", port 1 -> devpath "2", etc.
            target_devpath = str(self.port_number + 1)

            # Search for USB devices with subsystem 'usb' and device type 'usb_device'
            for device in context.list_devices(subsystem="usb", DEVTYPE="usb_device"):
                # Check if this device is under a vhci_hcd controller
                if "vhci_hcd" in device.sys_path:
                    # Check the devpath attribute to match our port
                    devpath = device.attributes.get("devpath")
                    if devpath and devpath.decode("utf-8").strip() == target_devpath:
                        logger.debug(
                            f"Port {self.port_number}: Found device "
                            f"at {device.sys_path}"
                        )
                        found_devices = self._find_dev_files(
                            context, Path(device.sys_path)
                        )
                        devices.extend(found_devices)
                        if devices:
                            return devices
        except Exception as e:
            logger.debug(
                f"Error finding local devices for port {self.port_number}: {e}"
            )

        return devices

    def _find_dev_files(
        self, context: pyudev.Context, sys_device_path: Path
    ) -> list[str]:
        """Find /dev files associated with a sysfs device path using pyudev.

        Args:
            context: pyudev Context object
            sys_device_path: Path to device in /sys/bus/usb/devices/

        Returns:
            List of /dev file paths
        """
        dev_files = set()

        try:
            # Create a device from the sysfs path
            base_device = pyudev.Devices.from_path(context, str(sys_device_path))

            # Wait for child devices to stabilize by polling until the device count
            # stops changing (e.g., block devices, partitions being created)
            max_attempts = 10
            stable_count = 0
            previous_count = 0

            for _ in range(max_attempts):
                current_files = set()

                # Get all child devices with device nodes
                for device in context.list_devices(parent=base_device):
                    if device.device_node:
                        current_files.add(device.device_node)

                # Also check if the base device itself has a device node
                if base_device.device_node:
                    current_files.add(base_device.device_node)

                # Check if the count has stabilized
                if len(current_files) == previous_count:
                    stable_count += 1
                    # If stable for 2 consecutive checks, we're done
                    if stable_count >= 2:
                        dev_files = current_files
                        break
                else:
                    stable_count = 0
                    previous_count = len(current_files)
                    dev_files = current_files

                # Small delay between polls
                sleep(0.1)

        except Exception as e:
            logger.debug(f"Error finding dev files for {sys_device_path}: {e}")

        return list(dev_files)

    def detach(self) -> None:
        """Detach this port from the local system."""

        # don't raise an exception if detach fails because the port may already
        # be detached
        run_command(
            ["sudo", "usbip", "detach", "-p", str(self.port_number)], check=False
        )

    def __repr__(self) -> str:
        return (
            f"- Port {self.port_number}:\n  "
            f"{self.description}\n  "
            f"busid: {self.remote_busid} from {self.server}\n  "
            f"local devices: "
            f"{', '.join(self.local_devices) if self.local_devices else 'none'}"
        )

    @staticmethod
    def list_ports() -> list["Port"]:
        """Lists the local usbip ports in use.

        Returns:
            A list of Port objects, each representing a port in use.
            Returns empty list if unable to query ports (e.g., vhci_hcd not loaded).
        """

        try:
            result = run_command(["sudo", "usbip", "port"], check=False)
            if result.returncode != 0:
                logger.debug(f"usbip port command failed: {result.stderr}")
                return []

            output = result.stdout
            ports: list[Port] = []
            for match in re_ports.finditer(output):
                port_info = match.groupdict()
                ports.append(Port(**port_info))
            logger.debug(f"Found {len(ports)} active usbip ports")
            return ports
        except Exception as e:
            logger.debug(f"Error listing ports: {e}")
            return []

    @classmethod
    def get_port_by_remote_busid(
        cls, remote_busid: str, server: str, retries=0
    ) -> "Port | None":
        """Get a Port object by its remote busid.

        Args:
            server: The server ip address to search.
            remote_busid: The remote busid to search for.

        Returns:
            The Port of the local mount of the remote device if found, otherwise None.
            There can be only one match as port ids are unique per server.
        """

        # after initiating an attach, it may take a moment for the port to appear -
        # retry a few times if not found immediately
        for attempt in range(retries + 1):
            ports = cls.list_ports()
            for port in ports:
                if port.remote_busid == remote_busid and port.server == server:
                    logger.info(f"Device attached on local port {port.port}")
                    return port
            if attempt < retries:
                sleep(0.2)

        return None
