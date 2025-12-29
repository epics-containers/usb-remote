"""
Fixtures for system integration tests.

These fixtures provide mocked subprocess.run for USB/IP commands,
and real server and client service instances running in background threads.
"""

import os
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# Unset INVOCATION_ID at module level to prevent systemd socket detection
_original_invocation_id = os.environ.pop("INVOCATION_ID", None)


@pytest.fixture
def mock_subprocess_run():
    """
    Mock subprocess.run to simulate USB/IP commands.

    This fixture returns a mock that responds appropriately to:
    - lsusb commands (for device enumeration)
    - usbip bind/unbind commands (server side)
    - usbip attach/detach commands (client side)
    - usbip port commands (for checking attached devices)
    """

    # Track attached devices: {(server, busid): port_number}
    attached_devices = {}
    next_port = [0]  # Use list to allow mutation in nested function

    def run_side_effect(command, *args, **kwargs):
        """Simulate subprocess.run behavior for USB/IP commands."""

        # Mock lsusb output for device enumeration
        if command[0] == "lsusb" and len(command) == 3 and command[1] == "-s":
            # lsusb -s 001:002
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout="Bus 001 Device 002: ID 2e8a:000a Raspberry Pi Pico",
                stderr="",
            )

        # Mock lsusb -v output for detailed device info
        elif command[0] == "lsusb" and "-v" in command:
            # This is used by get_devices() to enumerate all devices
            lsusb_output = """
Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
Bus 001 Device 002: ID 2e8a:000a Raspberry Pi Pico
  idVendor           0x2e8a Raspberry Pi
  idProduct          0x000a
  iSerial                 3 E12345678901234
  bDeviceClass            0
  bDeviceSubClass         0
  bDeviceProtocol         0

Bus 002 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
Bus 002 Device 003: ID 0483:5740 STMicroelectronics Virtual COM Port
  idVendor           0x0483 STMicroelectronics
  idProduct          0x5740
  iSerial                 3 ABC123456789
  bDeviceClass            2
  bDeviceSubClass         0
  bDeviceProtocol         0
"""
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout=lsusb_output,
                stderr="",
            )

        # Mock usbip list -pl for device enumeration (used by get_devices)
        elif command[0] == "usbip" and "list" in command and "-pl" in command:
            # This returns parseable format: busid=X#usbid=vendor:product#
            usbip_output = (
                "busid=1-1.1#usbid=2e8a:000a#\nbusid=2-2.1#usbid=0483:5740#\n"
            )
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout=usbip_output,
                stderr="",
            )

        # Mock usbip list --local for device enumeration
        elif command[0] == "usbip" and "list" in command and "--local" in command:
            # This is used by older get_devices() implementations
            usbip_output = """
 - busid 1-1.1 (2e8a:000a)
   Raspberry Pi : Pico (2e8a:000a)

 - busid 2-2.1 (0483:5740)
   STMicroelectronics : Virtual COM Port (0483:5740)
"""
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout=usbip_output,
                stderr="",
            )

        # Mock sudo usbip bind commands (server side)
        elif command[0] == "sudo" and command[1] == "usbip" and command[2] == "bind":
            # sudo usbip bind -b 1-1.1
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout="bind device on busid 1-1.1: complete",
                stderr="",
            )

        # Mock sudo usbip unbind commands (server side)
        elif command[0] == "sudo" and command[1] == "usbip" and command[2] == "unbind":
            # sudo usbip unbind -b 1-1.1
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout="unbind device on busid 1-1.1: complete",
                stderr="",
            )

        # Mock sudo usbip attach commands (client side)
        elif command[0] == "sudo" and command[1] == "usbip" and command[2] == "attach":
            # sudo usbip attach -r localhost -b 1-1.1
            # Extract server and busid from command
            server = command[4] if len(command) > 4 else "localhost"
            busid = command[6] if len(command) > 6 else "1-1.1"
            port = next_port[0]
            attached_devices[(server, busid)] = port
            next_port[0] += 1
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout="",
                stderr="",
            )

        # Mock sudo usbip detach commands (client side)
        elif command[0] == "sudo" and command[1] == "usbip" and command[2] == "detach":
            # sudo usbip detach -p 00
            port = command[4] if len(command) > 4 else "0"
            # Remove the device with this port from attached_devices
            for key, value in list(attached_devices.items()):
                if str(value) == port:
                    del attached_devices[key]
                    break
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout="",
                stderr="",
            )

        # Mock usbip port command (to check attached devices)
        elif command[0] in ("usbip", "sudo") and "port" in command:
            # Return attached devices
            if not attached_devices:
                usbip_port_output = """Imported USB devices
====================
"""
            else:
                usbip_port_output = "Imported USB devices\n====================\n"
                for (server, busid), port in attached_devices.items():
                    usbip_port_output += f"""Port {port:02d}: <Port in Use>
       Raspberry Pi Pico
       1-1 (2e8a:000a)
           -> usbip://{server}:3240/{busid}
           -> remote bus/dev 001/002

"""
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout=usbip_port_output,
                stderr="",
            )

        # Default: return success for any other command
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="",
            stderr="",
        )

    with patch("subprocess.run", side_effect=run_side_effect):
        # Also patch it in the utility module since that's where run_command imports it
        # Use the same side_effect so both patches behave the same way
        with patch(
            "usb_remote.utility.subprocess.run", side_effect=run_side_effect
        ) as mock_run2:
            # Mock usb.core.find to return fake USB device objects
            def mock_usb_find(
                idVendor=None,  # noqa: N803
                idProduct=None,  # noqa: N803
                bus=None,
                custom_match=None,
            ):
                """Mock usb.core.find to return a fake USB device."""
                import usb.core

                # Create a mock USB device that inherits from usb.core.Device
                # This is needed to pass the `type(device) is usb.core.Device` check
                class MockUSBDevice(usb.core.Device):
                    def __init__(self, bus, address, port_numbers, serial_number):
                        # Don't call parent __init__ as it requires real USB device
                        # Set attributes directly on __dict__ to bypass property
                        # descriptors
                        self.__dict__["bus"] = bus
                        self.__dict__["address"] = address
                        self.__dict__["port_numbers"] = port_numbers
                        self.__dict__["serial_number"] = serial_number

                # Determine which device to create based on vendor/product
                if idVendor == 0x2E8A and idProduct == 0x000A:
                    mock_device = MockUSBDevice(
                        bus=bus if bus else 1,
                        address=2,
                        port_numbers=(1, 1),
                        serial_number="E12345678901234",
                    )
                    # Override __class__ so type() returns usb.core.Device
                    mock_device.__class__ = usb.core.Device  # type: ignore
                elif idVendor == 0x0483 and idProduct == 0x5740:
                    mock_device = MockUSBDevice(
                        bus=2,
                        address=3,
                        port_numbers=(2, 1),
                        serial_number="ABC123456789",
                    )
                    # Override __class__ so type() returns usb.core.Device
                    mock_device.__class__ = usb.core.Device  # type: ignore
                else:
                    mock_device = MockUSBDevice(
                        bus=bus if bus else 1,
                        address=2,
                        port_numbers=(1, 1),
                        serial_number="",
                    )
                    # Override __class__ so type() returns usb.core.Device
                    mock_device.__class__ = usb.core.Device  # type: ignore

                # Verify custom_match if provided
                if custom_match and not custom_match(mock_device):
                    return None

                return mock_device

            with patch("usb.core.find", side_effect=mock_usb_find):
                # Yield the utility mock since that's where actual calls go through
                yield mock_run2


@pytest.fixture
def server_port():
    """Provide a unique port for the test server."""
    import random

    return random.randint(10000, 60000)


@pytest.fixture
def server_instance(mock_subprocess_run, server_port, monkeypatch):
    """Launch a real CommandServer instance in a background thread."""
    # Import after mocks are set up
    from usb_remote.server import CommandServer

    # Set the server port via environment variable
    monkeypatch.setenv("USB_REMOTE_SERVER_PORT", str(server_port))
    server = CommandServer(host="127.0.0.1", port=server_port)

    # Start server in a background thread
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    # Wait for server to start
    max_attempts = 50
    for _ in range(max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.1)
                sock.connect(("127.0.0.1", server_port))
                break
        except (TimeoutError, ConnectionRefusedError):
            time.sleep(0.1)
    else:
        raise RuntimeError("Server failed to start")

    yield server

    # Cleanup
    server.stop()
    server_thread.join(timeout=2)


@pytest.fixture
def client_service_instance(
    mock_subprocess_run, server_port, server_instance, monkeypatch
):
    """Launch a real ClientService instance in a background thread."""
    # Import after mocks are set up
    from usb_remote.client_service import ClientService
    from usb_remote.config import UsbRemoteConfig

    # Use a temporary socket path
    socket_path = tempfile.mktemp(suffix=".sock", prefix="usb-remote-test-")

    # Patch the config to use our test server port

    test_config = UsbRemoteConfig(
        servers=["127.0.0.1"], server_port=server_port, timeout=0.5
    )
    monkeypatch.setattr("usb_remote.config.get_config", lambda: test_config)

    # Capture any exceptions from the service thread
    service_exception = None

    def start_with_exception_handling():
        nonlocal service_exception
        try:
            service.start()
        except Exception as e:
            service_exception = e
            import traceback

            traceback.print_exc()

    service = ClientService(socket_path=socket_path)

    # Start client service in a background thread
    service_thread = threading.Thread(target=start_with_exception_handling, daemon=True)
    service_thread.start()

    # Wait for service to start
    max_attempts = 50
    for _ in range(max_attempts):
        # Check if service thread hit an exception
        if service_exception is not None:
            raise RuntimeError(
                f"Client service failed with exception: {service_exception}"
            ) from service_exception

        if Path(socket_path).exists():
            # Try to connect to verify it's ready
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.1)
                    sock.connect(socket_path)
                    break
            except (TimeoutError, ConnectionRefusedError, FileNotFoundError):
                time.sleep(0.1)
        else:
            time.sleep(0.1)
    else:
        # Check if socket file was even created
        if not Path(socket_path).exists():
            raise RuntimeError(
                f"Client service failed to start - socket file never "
                f"created at {socket_path}"
            )
        raise RuntimeError(
            f"Client service failed to start - socket exists but "
            f"not accepting connections at {socket_path}"
        )

    yield service

    # Cleanup
    service.stop()
    service_thread.join(timeout=2)
    if Path(socket_path).exists():
        Path(socket_path).unlink()
