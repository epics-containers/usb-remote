"""
Module for working with local usbip ports.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from time import sleep

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
            # Find the vhci_hcd device for this port
            # vhci ports are organized under /sys/devices/platform/vhci_hcd.*/
            platform_path = Path("/sys/devices/platform")

            if not platform_path.exists():
                return devices

            # Search through vhci_hcd controllers
            for vhci_dir in platform_path.glob("vhci_hcd.*"):
                # Each controller has USB buses under it
                for usb_bus in vhci_dir.glob("usb*"):
                    bus_num = usb_bus.name.replace("usb", "")

                    # Look for the port device: format is typically {busnum}-{port}
                    # VHCI ports map directly:
                    #   port 0 -> {busnum}-1, port 1 -> {busnum}-2, etc.
                    # The device path is {busnum}-{port_number+1}
                    port_num = self.port_number + 1
                    device_path = usb_bus / f"{bus_num}-{port_num}"
                    if device_path.exists():
                        # Verify this is actually the right port by checking devpath
                        devpath_file = device_path / "devpath"
                        if devpath_file.exists():
                            devpath = devpath_file.read_text().strip()
                            # devpath should match our port number
                            if devpath != str(port_num):
                                logger.debug(
                                    f"Port {self.port_number}: Skipping {device_path}"
                                    f" - devpath={devpath} doesn't match expected"
                                    f" {port_num}"
                                )
                                continue

                        found_devices = self._find_dev_files(device_path)
                        devices.extend(found_devices)
                        if devices:
                            return devices
        except Exception as e:
            logger.debug(
                f"Error finding local devices for port {self.port_number}: {e}"
            )

        return devices

    def _find_dev_files(self, sys_device_path: Path) -> list[str]:
        """Find /dev files associated with a sysfs device path.

        Args:
            sys_device_path: Path to device in /sys/bus/usb/devices/

        Returns:
            List of /dev file paths
        """
        dev_files = set()
        visited = set()

        def _query_path(path: Path, depth: int = 0) -> None:
            """Recursively query a sysfs path and its children for device files."""
            # Limit recursion depth to prevent issues
            if depth > 10:
                return

            try:
                # Resolve symlinks and check if we've visited this path
                real_path = path.resolve()
                if real_path in visited:
                    return
                visited.add(real_path)

                # Check if this directory has a device node
                if (path / "dev").exists():
                    result = run_command(
                        ["udevadm", "info", "-q", "name", "-p", str(path)],
                        check=False,
                    )
                    dev_name = result.stdout.strip()
                    if dev_name and not dev_name.startswith("/sys"):
                        dev_path = (
                            f"/dev/{dev_name}"
                            if not dev_name.startswith("/")
                            else dev_name
                        )
                        dev_files.add(dev_path)

                # Recursively check immediate children, but skip subdirectories
                # that represent other USB devices (have a busnum file)
                if path.is_dir():
                    for child in path.iterdir():
                        if child.is_dir() and not child.is_symlink():
                            # Skip if this looks like another USB device
                            # (USB devices have files like busnum, devnum, etc.)
                            # But we want to descend into interface directories
                            # (which have names like 1-1:1.0)
                            if (child / "busnum").exists():
                                # This is another USB device, skip it
                                continue
                            _query_path(child, depth + 1)

            except Exception as e:
                logger.debug(f"Error querying {path}: {e}")

        try:
            _query_path(sys_device_path)
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
