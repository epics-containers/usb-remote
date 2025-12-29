"""
System integration tests that launch real server and client services.

These tests mock only subprocess.run to simulate USB/IP operations,
but otherwise run the full server and client service stack.
"""

import json
import os
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# NOTE: Don't import usb_remote modules at module level!
# They need to be imported AFTER mocks are set up in fixtures.
# Import them inside fixtures/tests instead.

# Unset INVOCATION_ID at module level to prevent systemd socket detection
_original_invocation_id = os.environ.pop("INVOCATION_ID", None)


@pytest.fixture(autouse=True)
def mock_subprocess_run():
    """
    Mock subprocess.run to simulate USB/IP commands.

    This fixture returns a mock that responds appropriately to:
    - lsusb commands (for device enumeration)
    - usbip bind/unbind commands (server side)
    - usbip attach/detach commands (client side)
    - usbip port commands (for checking attached devices)
    """

    def run_side_effect(command, *args, **kwargs):
        """Simulate subprocess.run behavior for USB/IP commands."""
        " ".join(command) if isinstance(command, list) else str(command)
        # Write to file to verify mock is called
        with open("/tmp/mock_debug.log", "a") as f:
            f.write(f"MOCK CALLED: {command!r}\n")
        print(f"DEBUG MOCK: Command called: {command!r}", flush=True)
        print(f"DEBUG MOCK: Command type: {type(command)}", flush=True)
        print(f"DEBUG MOCK: Args: {args}, Kwargs: {kwargs}", flush=True)

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
            print("DEBUG MOCK: Matched usbip list -pl!", flush=True)
            # This returns parseable format: busid=X#usbid=vendor:product#
            usbip_output = (
                "busid=1-1.1#usbid=2e8a:000a#\nbusid=2-2.1#usbid=0483:5740#\n"
            )
            print(f"DEBUG MOCK: Returning usbip output: {usbip_output!r}", flush=True)
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
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout="",
                stderr="",
            )

        # Mock sudo usbip detach commands (client side)
        elif command[0] == "sudo" and command[1] == "usbip" and command[2] == "detach":
            # sudo usbip detach -p 00
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout="",
                stderr="",
            )

        # Mock usbip port command (to check attached devices)
        elif command[0] == "usbip" and command[1] == "port":
            # Return empty initially, or with an attached device
            # For now, return empty to simplify test
            usbip_port_output = """Imported USB devices
====================
"""
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout=usbip_port_output,
                stderr="",
            )

        # Default: return success for any other command
        print(
            f"DEBUG MOCK: No condition matched, returning empty result for: {command!r}",
            flush=True,
        )
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="",
            stderr="",
        )

    # Test that the mock is set up correctly
    print("DEBUG: Setting up subprocess.run mock")

    with patch("subprocess.run", side_effect=run_side_effect) as mock_run:
        # Also patch it in the utility module since that's where run_command imports it
        with patch("usb_remote.utility.subprocess.run", side_effect=run_side_effect):
            print("DEBUG: Mock patches applied")

            # Mock usb.core.find to return fake USB device objects
            def mock_usb_find(
                idVendor=None,
                idProduct=None,
                bus=None,
                custom_match=None,  # type: ignore
            ):
                """Mock usb.core.find to return a fake USB device."""
                print(
                    f"DEBUG USB MOCK: Called with idVendor={idVendor:#x} if idVendor "
                    f"else None, idProduct={idProduct:#x} if idProduct else None, "
                    f"bus={bus}, custom_match={custom_match}",
                    flush=True,
                )

                # Create a mock USB device with the requested properties
                mock_device = MagicMock()
                mock_device.bus = bus if bus else 1
                mock_device.address = 2  # Device address on the bus
                mock_device.port_numbers = (1, 1)  # Port numbers for busid 1-1.1

                # Set vendor/product based on what was requested
                if idVendor == 0x2E8A and idProduct == 0x000A:
                    print("DEBUG USB MOCK: Matched Raspberry Pi Pico", flush=True)
                    mock_device.serial_number = "E12345678901234"
                    mock_device.port_numbers = (1, 1)
                elif idVendor == 0x0483 and idProduct == 0x5740:
                    print("DEBUG USB MOCK: Matched STM device", flush=True)
                    mock_device.serial_number = "ABC123456789"
                    mock_device.port_numbers = (2, 1)
                    mock_device.bus = 2
                    mock_device.address = 3
                else:
                    print("DEBUG USB MOCK: No match for vendor/product", flush=True)
                    mock_device.serial_number = ""

                # Verify custom_match if provided
                if custom_match:
                    match_result = custom_match(mock_device)
                    print(
                        f"DEBUG USB MOCK: custom_match returned {match_result}",
                        flush=True,
                    )
                    if not match_result:
                        return None

                print(
                    f"DEBUG USB MOCK: Returning device with bus={mock_device.bus},"
                    f" port_numbers={mock_device.port_numbers}",
                    flush=True,
                )
                return mock_device

            with patch("usb.core.find", side_effect=mock_usb_find):
                yield mock_run


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
            print(f"DEBUG: Exception in service.start(): {e}")
            import traceback

            traceback.print_exc()

    service = ClientService(socket_path=socket_path)
    print(f"DEBUG: ClientService created with socket_path={socket_path}")

    # Start client service in a background thread
    service_thread = threading.Thread(target=start_with_exception_handling, daemon=True)
    service_thread.start()
    print("DEBUG: Client service thread started")

    # Wait for service to start
    max_attempts = 50
    for attempt in range(max_attempts):
        # Check if service thread hit an exception
        if service_exception is not None:
            raise RuntimeError(
                f"Client service failed with exception: {service_exception}"
            ) from service_exception

        if Path(socket_path).exists():
            print(f"DEBUG: Socket file exists at attempt {attempt}")
            # Try to connect to verify it's ready
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.1)
                    sock.connect(socket_path)
                    print("DEBUG: Successfully connected to socket")
                    break
            except (TimeoutError, ConnectionRefusedError, FileNotFoundError) as e:
                print(f"DEBUG: Connection failed at attempt {attempt}: {e}")
                time.sleep(0.1)
        else:
            if attempt % 10 == 0:
                print(f"DEBUG: Socket file doesn't exist yet at attempt {attempt}")
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


class TestSystemIntegration:
    """System integration tests with real server and client service."""

    def test_attach_via_client_service(
        self,
        server_instance,
        client_service_instance,
        mock_subprocess_run,
    ):
        """
        Test attaching a USB device via the client service.

        This test:
        1. Has a real server running that can list and bind devices
        2. Has a real client service running that accepts socket commands
        3. Sends an attach command to the client service socket
        4. Verifies the full flow works end-to-end
        """
        # Import after mocks are set up
        from usb_remote.client_api import ClientDeviceRequest

        # Create the attach request, specifying the host so it uses our test server
        request = ClientDeviceRequest(
            command="attach",
            bus="1-1.1",  # This bus_id matches our mock device
            host="127.0.0.1",  # Use our test server
        )

        # Send request to client service via Unix socket
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(client_service_instance.socket_path)
            sock.sendall(request.model_dump_json().encode("utf-8"))

            # Receive response
            response_data = sock.recv(4096).decode("utf-8")

        # Parse response
        response = json.loads(response_data)

        # Verify response structure
        assert response["status"] == "success"
        assert "data" in response
        assert response["data"]["bus_id"] == "1-1.1"
        assert response["data"]["vendor_id"] == "2e8a"
        assert response["data"]["product_id"] == "000a"
        assert "Raspberry Pi" in response["data"]["description"]
        assert response["server"] == "127.0.0.1"

        # Verify that subprocess.run was called with the expected commands
        # Check that we called usbip bind on the server
        bind_calls = [
            call
            for call in mock_subprocess_run.call_args_list
            if call[0][0][0] == "sudo"
            and len(call[0][0]) > 2
            and call[0][0][1] == "usbip"
            and call[0][0][2] == "bind"
        ]
        assert len(bind_calls) >= 1, "Server should have called usbip bind"

        # Check that we called usbip attach on the client
        attach_calls = [
            call
            for call in mock_subprocess_run.call_args_list
            if call[0][0][0] == "sudo"
            and len(call[0][0]) > 2
            and call[0][0][1] == "usbip"
            and call[0][0][2] == "attach"
        ]
        assert len(attach_calls) >= 1, "Client should have called usbip attach"
