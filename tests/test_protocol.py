"""Unit tests for the client-server protocol.

This test suite validates the communication protocol between the usb-remote client
and server, including:

1. Request/Response Serialization:
   - ListRequest/ListResponse for querying available USB devices
   - AttachRequest/AttachResponse for attaching devices
   - ErrorResponse for error handling

2. Client-Server Integration:
   - Full request-response cycles
   - Error handling and propagation
   - Edge cases (empty requests, invalid JSON, unknown commands)

3. Protocol Robustness:
   - Field validation and defaults
   - Serialization/deserialization roundtrips
   - Handling of optional and null fields
"""

import json
import socket
import threading
import time
from unittest.mock import patch

import pytest

from usb_remote.api import (
    DeviceRequest,
    DeviceResponse,
    ErrorResponse,
    ListRequest,
    ListResponse,
)
from usb_remote.server import CommandServer
from usb_remote.usbdevice import UsbDevice


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
def server_port():
    """Provide a unique port for each test to avoid conflicts."""
    import random

    return random.randint(10000, 60000)


@pytest.fixture
def mock_get_devices(mock_usb_devices):
    """Mock the get_devices function."""
    with patch("usb_remote.server.get_devices", return_value=mock_usb_devices):
        yield


@pytest.fixture
def mock_get_device(mock_usb_devices):
    """Mock the get_device function."""
    with patch("usb_remote.server.get_device", return_value=mock_usb_devices[0]):
        yield


@pytest.fixture
def mock_run_command():
    """Mock the run_command function to avoid actual system calls."""
    with patch("usb_remote.server.run_command"):
        yield


@pytest.fixture
def server(server_port, mock_get_devices, mock_get_device, mock_run_command):
    """Create and start a test server."""
    srv = CommandServer(host="127.0.0.1", port=server_port)

    # Start server in a separate thread
    server_thread = threading.Thread(target=srv.start)
    server_thread.daemon = True
    server_thread.start()

    # Give server time to start
    time.sleep(0.1)

    yield srv

    # Cleanup
    srv.stop()


class TestListRequest:
    """Test the list request protocol."""

    def test_list_request_serialization(self):
        """Test that ListRequest serializes correctly."""
        request = ListRequest()
        json_data = request.model_dump_json()
        parsed = json.loads(json_data)

        assert parsed["command"] == "list"

    def test_list_request_default_command(self):
        """Test that ListRequest has correct default command."""
        request = ListRequest()
        assert request.command == "list"

    def test_list_response_serialization(self, mock_usb_devices):
        """Test that ListResponse serializes correctly."""
        response = ListResponse(status="success", data=mock_usb_devices)
        json_data = response.model_dump_json()
        parsed = json.loads(json_data)

        assert parsed["status"] == "success"
        assert len(parsed["data"]) == 2
        assert parsed["data"][0]["bus_id"] == "1-1.1"
        assert parsed["data"][0]["vendor_id"] == "1234"

    def test_list_response_deserialization(self, mock_usb_devices):
        """Test that ListResponse deserializes correctly."""
        response = ListResponse(status="success", data=mock_usb_devices)
        json_data = response.model_dump_json()

        # Deserialize
        deserialized = ListResponse.model_validate_json(json_data)

        assert deserialized.status == "success"
        assert len(deserialized.data) == 2
        assert deserialized.data[0].bus_id == "1-1.1"


class TestAttachRequest:
    """Test the attach request protocol."""

    def test_attach_request_with_id(self):
        """Test AttachRequest with device ID."""
        request = DeviceRequest(command="attach", id="1234:5678")
        json_data = request.model_dump_json()
        parsed = json.loads(json_data)

        assert parsed["command"] == "attach"
        assert parsed["id"] == "1234:5678"

    def test_attach_request_with_serial(self):
        """Test AttachRequest with serial number."""
        request = DeviceRequest(command="attach", serial="ABC123")
        json_data = request.model_dump_json()
        parsed = json.loads(json_data)

        assert parsed["command"] == "attach"
        assert parsed["serial"] == "ABC123"

    def test_attach_request_with_bus(self):
        """Test AttachRequest with bus ID."""
        request = DeviceRequest(command="attach", bus="1-1.1")
        json_data = request.model_dump_json()
        parsed = json.loads(json_data)

        assert parsed["command"] == "attach"
        assert parsed["bus"] == "1-1.1"

    def test_attach_request_first_flag(self):
        """Test AttachRequest with first flag."""
        request = DeviceRequest(command="attach", first=True)
        json_data = request.model_dump_json()
        parsed = json.loads(json_data)

        assert parsed["command"] == "attach"
        assert parsed["first"] is True

    def test_detach_request(self):
        """Test DetachRequest."""
        request = DeviceRequest(command="detach", bus="1-1.1")
        json_data = request.model_dump_json()
        parsed = json.loads(json_data)

        assert parsed["command"] == "detach"
        assert parsed["bus"] == "1-1.1"

    def test_attach_response_success(self, mock_usb_devices):
        """Test successful AttachResponse."""
        response = DeviceResponse(status="success", data=mock_usb_devices[0])
        json_data = response.model_dump_json()
        parsed = json.loads(json_data)

        assert parsed["status"] == "success"
        assert parsed["data"]["bus_id"] == "1-1.1"

    def test_attach_response_failure(self, mock_usb_devices):
        """Test failure AttachResponse."""
        response = DeviceResponse(status="failure", data=mock_usb_devices[0])
        json_data = response.model_dump_json()
        parsed = json.loads(json_data)

        assert parsed["status"] == "failure"


class TestErrorResponse:
    """Test the error response protocol."""

    def test_error_response_serialization(self):
        """Test that ErrorResponse serializes correctly."""
        response = ErrorResponse(status="error", message="Something went wrong")
        json_data = response.model_dump_json()
        parsed = json.loads(json_data)

        assert parsed["status"] == "error"
        assert parsed["message"] == "Something went wrong"

    def test_error_response_deserialization(self):
        """Test that ErrorResponse deserializes correctly."""
        json_data = '{"status": "error", "message": "Test error"}'
        response = ErrorResponse.model_validate_json(json_data)

        assert response.status == "error"
        assert response.message == "Test error"


class TestClientServerIntegration:
    """Integration tests for client-server communication."""

    def test_find_device_integration(self, server, server_port, mock_usb_devices):
        """Test full find device flow from client to server."""
        from usb_remote.client import find_device

        # Mock send_request to return a device response
        with patch("usb_remote.client.send_request") as mock_send:
            mock_send.return_value = DeviceResponse(
                status="success", data=mock_usb_devices[0]
            )
            device, server_name = find_device(
                server_hosts=["127.0.0.1"], id="1234:5678"
            )

            assert isinstance(device, UsbDevice)
            assert device.bus_id == "1-1.1"
            assert server_name == "127.0.0.1"

    def test_detach_device_integration(self, server, server_port, mock_usb_devices):
        """Test full detach device flow from client to server."""
        from usb_remote.client import detach_device

        # Mock Port.get_port_by_remote_busid to return None to avoid run_command call
        with (
            patch("usb_remote.client.send_request") as mock_send,
            patch("usb_remote.client.Port.get_port_by_remote_busid", return_value=None),
        ):
            detach_device(bus_id="1-1.1", server_host="127.0.0.1")
            # Verify send_request was called with correct parameters
            assert mock_send.called

    def test_server_handles_empty_request(self, server, server_port):
        """Test that server handles empty requests gracefully."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", server_port))
        # Close the write side to send EOF, which makes recv() return empty string
        sock.shutdown(socket.SHUT_WR)

        response = sock.recv(4096).decode("utf-8")
        sock.close()
        parsed = json.loads(response)

        assert parsed["status"] == "error"
        assert "Empty or invalid" in parsed["message"]

    def test_server_handles_invalid_json(self, server, server_port):
        """Test that server handles invalid JSON gracefully."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5.0)  # Prevent hanging
            sock.connect(("127.0.0.1", server_port))
            sock.sendall(b"not valid json")

            response = sock.recv(4096).decode("utf-8")
            parsed = json.loads(response)

            assert parsed["status"] == "error"
            assert "Invalid request format" in parsed["message"]

    def test_server_handles_unknown_command(self, server, server_port):
        """Test that server handles unknown commands gracefully."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5.0)  # Prevent hanging
            sock.connect(("127.0.0.1", server_port))
            sock.sendall(b'{"command": "unknown"}')

            response = sock.recv(4096).decode("utf-8")
            parsed = json.loads(response)

            assert parsed["status"] == "error"


class TestProtocolRobustness:
    """Test protocol robustness and edge cases."""

    def test_request_with_all_fields_null(self):
        """Test AttachRequest with all optional fields as None."""
        request = DeviceRequest(
            command="attach",
            id=None,
            bus=None,
            serial=None,
            desc=None,
            first=False,
        )
        json_data = request.model_dump_json()
        parsed = json.loads(json_data)

        assert parsed["command"] == "attach"
        # Verify serialization includes null fields
        assert "id" in parsed
        assert "bus" in parsed

    def test_usb_device_serialization_roundtrip(self):
        """Test that UsbDevice can be serialized and deserialized."""
        device = UsbDevice(
            bus_id="1-1.1",
            vendor_id="1234",
            product_id="5678",
            bus=1,
            port_numbers=(1, 1),
            device_name="/dev/bus/usb/001/002",
            serial="ABC123",
            description="Test Device",
        )

        # Serialize
        json_data = device.model_dump_json()

        # Deserialize
        restored = UsbDevice.model_validate_json(json_data)

        assert restored.bus_id == device.bus_id
        assert restored.vendor_id == device.vendor_id
        assert restored.serial == device.serial
        assert restored.port_numbers == device.port_numbers

    def test_list_response_with_empty_list(self):
        """Test ListResponse with no devices."""
        response = ListResponse(status="success", data=[])
        json_data = response.model_dump_json()
        parsed = json.loads(json_data)

        assert parsed["status"] == "success"
        assert parsed["data"] == []

    def test_device_with_no_serial(self):
        """Test UsbDevice with no serial number."""
        device = UsbDevice(
            bus_id="1-1.1",
            vendor_id="1234",
            product_id="5678",
            bus=1,
            port_numbers=(1, 1),
            serial=None,
        )

        json_data = device.model_dump_json()
        restored = UsbDevice.model_validate_json(json_data)

        assert restored.serial is None


class TestErrorDifferentiation:
    """Test that server properly differentiates between error types."""

    def test_not_found_error_response(self):
        """Test that ErrorResponse handles not_found status."""
        response = ErrorResponse(
            status="not_found", message="No matching USB device found."
        )
        json_data = response.model_dump_json()
        parsed = json.loads(json_data)

        assert parsed["status"] == "not_found"
        assert parsed["message"] == "No matching USB device found."

    def test_multiple_matches_error_response(self):
        """Test that ErrorResponse handles multiple_matches status."""
        response = ErrorResponse(
            status="multiple_matches",
            message="Multiple matching USB devices found. Please refine your criteria.",
        )
        json_data = response.model_dump_json()
        parsed = json.loads(json_data)

        assert parsed["status"] == "multiple_matches"
        assert "Multiple matching" in parsed["message"]

    def test_server_returns_not_found(self, server_port):
        """Test that server returns not_found error when device doesn't exist."""
        from usb_remote.client import DeviceNotFoundError, send_request
        from usb_remote.server import CommandServer

        # Start a test server with empty device list
        with patch("usb_remote.server.get_devices", return_value=[]):
            server = CommandServer(host="127.0.0.1", port=server_port)
            server_thread = threading.Thread(target=server.start, daemon=True)
            server_thread.start()
            time.sleep(0.5)  # Wait for server to start

            try:
                # Send a find request that won't match anything
                request = DeviceRequest(
                    command="find",
                    id="9999:9999",  # Non-existent device
                )

                # Should raise DeviceNotFoundError
                with pytest.raises(DeviceNotFoundError, match="No matching"):
                    send_request(request, "127.0.0.1", server_port)

            finally:
                server.stop()

    def test_server_returns_multiple_matches(self, server_port, mock_usb_devices):
        """Test that server returns multiple_matches error when
        criteria match multiple devices."""
        from usb_remote.client import MultipleDevicesError, send_request
        from usb_remote.server import CommandServer

        # Create mock get_device that raises MultipleDevicesError
        def mock_get_device(**kwargs):
            from usb_remote.usbdevice import MultipleDevicesError

            raise MultipleDevicesError("Multiple matching USB devices found.")

        with (
            patch("usb_remote.server.get_devices", return_value=mock_usb_devices),
            patch("usb_remote.server.get_device", side_effect=mock_get_device),
        ):
            server = CommandServer(host="127.0.0.1", port=server_port)
            server_thread = threading.Thread(target=server.start, daemon=True)
            server_thread.start()
            time.sleep(0.5)  # Wait for server to start

            try:
                # Send a find request that matches multiple devices
                request = DeviceRequest(command="find", desc="Test")

                # Should raise MultipleDevicesError
                with pytest.raises(MultipleDevicesError, match="Multiple matching"):
                    send_request(request, "127.0.0.1", server_port)

            finally:
                server.stop()
