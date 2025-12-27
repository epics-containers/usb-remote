import fnmatch
import re
import subprocess

import usb.core
from pydantic import BaseModel, Field

from usb_remote.utility import run_command


class DeviceNotFoundError(Exception):
    """Raised when no USB device matches the search criteria."""


class MultipleDevicesError(Exception):
    """Raised when multiple USB devices match the search criteria."""


class UsbDevice(BaseModel):
    """Pydantic model representing a USB device."""

    bus_id: str
    vendor_id: str
    product_id: str
    bus: int = 0
    port_numbers: tuple[int, ...] = Field(default_factory=tuple)
    device_name: str = ""
    serial: str | None = ""
    description: str = "unknown"

    model_config = {"frozen": False}  # Allow field updates after creation

    def __str__(self):
        ser = f"\n  serial={self.serial}" if self.serial else ""
        return (
            f"- {self.description}{ser}\n"
            f"  id={self.vendor_id}:{self.product_id} bus={self.bus_id:13}"
        )

    @staticmethod
    def filter_on_port_numbers(
        device: usb.core.Device, port_numbers: tuple[int, ...]
    ) -> bool:
        """
        Custom filter function to match USB devices based on port numbers.

        e.g. When the bus ID is "1-2.3.4",
            the bus is 1 and the port numbers are (2, 3, 4).
        """
        device_ports = getattr(device, "port_numbers", ())
        return device_ports == port_numbers

    @classmethod
    def create(cls, bus_id: str, vendor_id: str, product_id: str) -> "UsbDevice":
        """
        Factory method to create a UsbDevice with all fields populated.

        This performs the work previously done in __post_init__ to query
        the USB device and populate additional fields.

        Args:
            bus_id: The bus ID string (e.g., "1-2.3.4")
            vendor_id: The vendor ID in hex format
            product_id: The product ID in hex format

        Returns:
            A fully populated UsbDevice instance
        """
        # Split bus_id into bus and port numbers
        bus_str, port_str = bus_id.split("-")
        bus = int(bus_str)
        port_numbers = tuple(int(p) for p in port_str.split("."))

        # Find the device
        device = usb.core.find(
            idVendor=int(vendor_id, 16),
            idProduct=int(product_id, 16),
            bus=bus,
            custom_match=lambda d: UsbDevice.filter_on_port_numbers(d, port_numbers),
        )
        assert type(device) is usb.core.Device, "Device not found"

        device_name = f"/dev/bus/usb/{device.bus:03d}/{device.address:03d}"
        serial = ""
        try:
            serial = getattr(device, "serial_number", "")
        except (ValueError, usb.core.USBError):
            pass  # leave serial as ""

        # It is very hard to get vendor and product strings due to permissions
        # so call out to lsusb which has no issue extracting them
        # UPDATE: when running as a system service, these are available for
        # most devices but the resulting descriptions are less informative.
        # (I don't fully understand where lsusb gets its description string from!)
        description = "unknown"
        try:
            lsusb_result = run_command(
                ["lsusb", "-s", f"{device.bus:03d}:{device.address:03d}"]
            )
            lsusb_output = lsusb_result.stdout.strip()
            desc_match = re.search(rf".*{vendor_id}:{product_id} (.+)$", lsusb_output)
            if desc_match:
                description = desc_match.group(1)
        except subprocess.CalledProcessError:
            pass  # leave description as "unknown"

        return cls(
            bus_id=bus_id,
            vendor_id=vendor_id,
            product_id=product_id,
            bus=bus,
            port_numbers=port_numbers,
            device_name=device_name,
            serial=serial,
            description=description,
        )


def get_device(
    id: str = "",
    bus: str = "",
    desc: str = "",
    first: bool = False,
    serial: str | None = None,
) -> UsbDevice:
    """
    Retrieve a USB device based on filtering criteria.

    Args:
        id: The device ID in the format "vendor:product" (e.g., "0bda:5400")
        bus: The bus ID string (e.g., "1-2.3.4")
        desc: A substring to match in the device description
        serial: The serial number to match
        first: Whether to return the first match or raise an error on multiple matches
    Returns:
        A UsbDevice instance matching the criteria.
    """
    devices = get_devices()
    filtered_devices = []

    for device in devices:
        if id:
            device_id = f"{device.vendor_id}:{device.product_id}"
            if not fnmatch.fnmatch(device_id.lower(), id.lower()):
                continue
        if bus and not fnmatch.fnmatch(device.bus_id.lower(), bus.lower()):
            continue
        # for desc, match a substring or glob pattern
        if desc and (
            not fnmatch.fnmatch(device.description, desc)
            and desc not in device.description
        ):
            continue
        if serial and device.serial and not fnmatch.fnmatch(device.serial, serial):
            continue
        filtered_devices.append(device)

    if not filtered_devices:
        raise DeviceNotFoundError("No matching USB device found.")

    if first:
        return filtered_devices[0]

    if len(filtered_devices) > 1:
        device_list = "\n".join(
            f"  - {d.description} (id={d.vendor_id}:{d.product_id}, bus={d.bus_id})"
            for d in filtered_devices
        )
        raise MultipleDevicesError(
            f"Multiple matching USB devices found. Please refine your criteria.\n"
            f"Matching devices:\n{device_list}"
        )

    return filtered_devices[0]


def get_devices() -> list[UsbDevice]:
    """
    Retrieve a list of connected USB devices that can be shared over usbip.

    Returns:
        list: A list of connected USB devices.
    """
    # Call the system CLI usbip list -lp to get a list of shareable USB devices
    result = run_command(["usbip", "list", "-pl"])
    pattern = r"busid=([^#]+)#usbid=([0-9a-f]+):([0-9a-f]+)#"

    # Parse the output and extract detailed information for each device
    devices: list[UsbDevice] = []
    for match in re.finditer(pattern, result.stdout, re.DOTALL):
        busid, vendor, product = match.groups()
        devices.append(UsbDevice.create(busid, vendor, product))
    return devices
