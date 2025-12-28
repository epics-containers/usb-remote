"""Shared fixtures and mock functions for CLI tests."""

import subprocess
from unittest.mock import Mock, patch

import pytest

from usb_remote.api import DeviceResponse, ErrorResponse, ListResponse
from usb_remote.config import UsbRemoteConfig
from usb_remote.usbdevice import UsbDevice


@pytest.fixture
def mock_config():
    """Mock config to return just localhost as a server."""
    config = UsbRemoteConfig(servers=["localhost"], timeout=0.1)
    with patch("usb_remote.config.get_config", return_value=config):
        yield config


@pytest.fixture
def mock_usb_devices():
    """Create mock USB devices for testing."""
    return [
        UsbDevice(
            bus_id="1-1.1",
            vendor_id="1234",
            product_id="5678",
            bus=1,
            port_numbers=(1, 1),
            device_name="/dev/bus/usb/001/002",
            serial="ABC123",
            description="Test Device 1",
        ),
        UsbDevice(
            bus_id="2-2.1",
            vendor_id="abcd",
            product_id="ef01",
            bus=2,
            port_numbers=(2, 1),
            device_name="/dev/bus/usb/002/003",
            serial="XYZ789",
            description="Test Device 2",
        ),
    ]


@pytest.fixture
def mock_socket_for_list(mock_usb_devices):
    """Create a mock socket that returns ListResponse with devices."""

    def _create_mock_socket(devices=None):
        if devices is None:
            devices = mock_usb_devices
        mock_sock = Mock()
        mock_sock.recv.return_value = (
            ListResponse(
                status="success",
                data=devices,
            )
            .model_dump_json()
            .encode("utf-8")
        )
        mock_sock.__enter__ = Mock(return_value=mock_sock)
        mock_sock.__exit__ = Mock(return_value=False)
        return mock_sock

    return _create_mock_socket


@pytest.fixture
def mock_socket(mock_usb_devices):
    """Create a mock socket that returns DeviceResponse."""

    def _create_mock_socket(device=None):
        if device is None:
            device = mock_usb_devices[0]
        mock_sock = Mock()
        mock_sock.recv.return_value = (
            DeviceResponse(
                status="success",
                data=device,
            )
            .model_dump_json()
            .encode("utf-8")
        )
        mock_sock.__enter__ = Mock(return_value=mock_sock)
        mock_sock.__exit__ = Mock(return_value=False)
        return mock_sock

    return _create_mock_socket


def create_error_socket():
    """Create a mock socket that returns an error response."""
    mock_sock = Mock()
    mock_sock.recv.return_value = (
        ErrorResponse(
            status="not_found",
            message="Device not found",
        )
        .model_dump_json()
        .encode("utf-8")
    )
    mock_sock.__enter__ = Mock(return_value=mock_sock)
    mock_sock.__exit__ = Mock(return_value=False)
    return mock_sock


def mock_subprocess_run(command, **kwargs):
    """Mock subprocess.run to simulate command execution."""
    result = Mock(spec=subprocess.CompletedProcess)
    result.returncode = 0
    result.stdout = ""
    result.stderr = ""

    cmd_str = " ".join(command) if isinstance(command, list) else command

    # Mock usbip list -pl command - return local USB devices
    if "usbip list" in cmd_str and "-pl" in cmd_str:
        result.stdout = """busid=1-1.1#usbid=1234:5678#
busid=2-2.1#usbid=abcd:ef01#
"""

    # Mock usbip port command - return a realistic port listing
    elif "usbip port" in cmd_str:
        # Extract remote host if available from previous attach command context
        # Use the captured host from attach command, or default to localhost
        remote_host = getattr(mock_subprocess_run, "_test_context_host", "localhost")

        # Only return a port if attach has been called
        # This prevents timeouts during detach_local_device's port lookup
        if getattr(mock_subprocess_run, "_attach_called", False):
            # Simulate an attached device on port 00
            result.stdout = f"""Imported USB devices
====================
Port 00: <Port in Use> at Full Speed(12Mbps)
       Test Device 1 : unknown product (1234:5678)
       1-1.1 -> usbip://{remote_host}:3240/1-1.1
           -> remote bus/dev 001/002
"""
        else:
            # No devices attached yet
            result.stdout = "Imported USB devices\n====================\n"

    # Mock usbip attach command
    elif "usbip attach" in cmd_str:
        # Capture the remote host for port command
        # Command format: ['sudo', 'usbip', 'attach', '-r', 'hostname', '-b', 'busid']
        try:
            if "-r" in command:
                idx = command.index("-r")
                if idx + 1 < len(command):
                    # AI added these to give the mock function context
                    # TODO: is this a good practice?
                    mock_subprocess_run._test_context_host = command[idx + 1]  # type: ignore
                    mock_subprocess_run._attach_called = True  # type: ignore
        except (ValueError, IndexError):
            pass
        result.stdout = ""

    # Mock usbip detach command
    elif "usbip detach" in cmd_str:
        result.stdout = ""

    # Mock udevadm commands - return device file paths
    elif "udevadm info" in cmd_str:
        if "-q all" in cmd_str:
            # Mock udevadm info -q all output with DEVNAME
            result.stdout = """E: DEVNAME=bus/usb/001/002
E: DEVTYPE=usb_device
E: ID_BUS=usb
"""
        elif "-q name" in cmd_str:
            # Return device file names based on the path
            if "tty" in cmd_str.lower():
                result.stdout = "ttyACM0"
            elif "video" in cmd_str.lower():
                result.stdout = "video0"
            elif "hidraw" in cmd_str.lower():
                result.stdout = "hidraw0"
            else:
                result.stdout = ""

    return result
