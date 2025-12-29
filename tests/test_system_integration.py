"""
System integration tests that launch real server and client services.

These tests mock only subprocess.run to simulate USB/IP operations,
but otherwise run the full server and client service stack.
"""

import json
import socket

import pytest

# get the fixture definitions


class TestSystemIntegration:
    """System integration tests with real server and client service."""

    @pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
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
            if len(call.args) > 0
            and len(call.args[0]) > 2
            and call.args[0][0] == "sudo"
            and call.args[0][1] == "usbip"
            and call.args[0][2] == "bind"
        ]
        assert len(bind_calls) >= 1, "Server should have called usbip bind"

        # Check that we called usbip attach on the client
        attach_calls = [
            call
            for call in mock_subprocess_run.call_args_list
            if len(call.args) > 0
            and len(call.args[0]) > 2
            and call.args[0][0] == "sudo"
            and call.args[0][1] == "usbip"
            and call.args[0][2] == "attach"
        ]
        assert len(attach_calls) >= 1, "Client should have called usbip attach"

    @pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
    def test_detach_via_client_service(
        self,
        server_instance,
        client_service_instance,
        mock_subprocess_run,
    ):
        """
        Test detaching a USB device via the client service.

        This test:
        1. Has a real server running that can unbind devices
        2. Has a real client service running that accepts socket commands
        3. First attaches a device to set up state
        4. Sends a detach command to the client service socket
        5. Verifies the full flow works end-to-end
        """
        # Import after mocks are set up
        from usb_remote.client_api import ClientDeviceRequest

        # First, attach a device so we have something to detach
        attach_request = ClientDeviceRequest(
            command="attach",
            bus="1-1.1",
            host="127.0.0.1",
        )
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(client_service_instance.socket_path)
            sock.sendall(attach_request.model_dump_json().encode("utf-8"))
            sock.recv(4096)  # Wait for attach to complete

        # Now detach the device
        detach_request = ClientDeviceRequest(
            command="detach",
            bus="1-1.1",  # This bus_id matches our mock device
            host="127.0.0.1",  # Use our test server
        )

        # Send request to client service via Unix socket
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(client_service_instance.socket_path)
            sock.sendall(detach_request.model_dump_json().encode("utf-8"))

            # Receive response
            response_data = sock.recv(4096).decode("utf-8")

        # Parse response
        response = json.loads(response_data)

        # Verify response structure
        assert response["status"] == "success"
        assert "data" in response
        assert response["data"]["bus_id"] == "1-1.1"
        assert response["server"] == "127.0.0.1"

        # Verify that subprocess.run was called with the expected commands
        # Check that we called usbip unbind on the server
        unbind_calls = [
            call
            for call in mock_subprocess_run.call_args_list
            if len(call.args) > 0
            and len(call.args[0]) > 2
            and call.args[0][0] == "sudo"
            and call.args[0][1] == "usbip"
            and call.args[0][2] == "unbind"
        ]
        assert len(unbind_calls) >= 1, "Server should have called usbip unbind"

        # Check that we called usbip detach on the client
        detach_calls = [
            call
            for call in mock_subprocess_run.call_args_list
            if len(call.args) > 0
            and len(call.args[0]) > 2
            and call.args[0][0] == "sudo"
            and call.args[0][1] == "usbip"
            and call.args[0][2] == "detach"
        ]
        assert len(detach_calls) >= 1, "Client should have called usbip detach"
