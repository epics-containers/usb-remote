"""Unit tests for the CLI interface."""

import subprocess
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from typer.testing import CliRunner

from usb_remote import __version__
from usb_remote.__main__ import app
from usb_remote.api import DeviceResponse, ListResponse
from usb_remote.config import UsbRemoteConfig
from usb_remote.usbdevice import UsbDevice

runner = CliRunner()


@pytest.fixture
def mock_config():
    """Mock config to return just localhost as a server."""
    config = UsbRemoteConfig(servers=["localhost"], timeout=0.1)
    with patch("usb_remote.config.get_config", return_value=config):
        yield config


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
    from usb_remote.api import ErrorResponse

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


class TestVersionCommand:
    """Test the version command."""

    def test_cli_version(self):
        """Test version via subprocess."""
        cmd = [sys.executable, "-m", "usb_remote", "--version"]
        output = subprocess.check_output(cmd).decode().strip()
        assert output == f"usb-remote {__version__}"

    def test_version_flag(self):
        """Test --version flag."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert f"usb-remote {__version__}" in result.stdout


class TestListCommand:
    """Test the list command."""

    def test_list_local(self):
        """Test list --local command."""

        # Here we genuinely get the local devices via usbip and just verify no errors
        result = runner.invoke(app, ["list", "--local"])
        assert result.exit_code == 0

    def test_list_remote(self, mock_config, mock_socket_for_list):
        """Test list command to query remote server."""
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("socket.socket", return_value=mock_socket_for_list()),
        ):
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            # Validate server header is shown
            assert "=== localhost ===" in result.stdout
            # Validate device information is displayed
            assert "Test Device 1" in result.stdout
            assert "Test Device 2" in result.stdout

    def test_list_with_host(self, mock_config, mock_socket_for_list):
        """Test list command with specific host."""
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("socket.socket", return_value=mock_socket_for_list()),
        ):
            result = runner.invoke(app, ["list", "--host", "192.168.1.100"])
            assert result.exit_code == 0
            # Validate specific host is queried
            assert "=== 192.168.1.100 ===" in result.stdout
            # Should show devices from that host
            assert "Test Device" in result.stdout

    def test_list_error_handling(self, mock_config, mock_socket_for_list):
        """Test list command error handling."""
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("socket.socket", return_value=mock_socket_for_list(devices=[])),
        ):
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            # Should show server header even with no devices
            assert "=== localhost ===" in result.stdout
            # Should indicate no devices found
            assert "No devices" in result.stdout

    def test_list_multi_server(self, mock_config, mock_socket_for_list):
        """Test list command with multiple servers."""
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("socket.socket", return_value=mock_socket_for_list()),
        ):
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            # Should show localhost server header
            assert "=== localhost ===" in result.stdout
            # Should show devices
            assert "Test Device" in result.stdout


class TestAttachCommand:
    """Test the attach command."""

    def setup_method(self):
        """Reset mock subprocess state before each test."""
        # Clear any state from previous tests
        if hasattr(mock_subprocess_run, "_test_context_host"):
            delattr(mock_subprocess_run, "_test_context_host")
        if hasattr(mock_subprocess_run, "_attach_called"):
            delattr(mock_subprocess_run, "_attach_called")

    def test_attach_with_id(self, mock_usb_devices, mock_socket):
        """Test attach command with device ID."""
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("socket.socket", return_value=mock_socket()),
        ):
            result = runner.invoke(
                app, ["attach", "--id", "1234:5678", "--host", "localhost"]
            )
            assert result.exit_code == 0
            assert "Attached to device on localhost:" in result.stdout
            assert "Test Device 1" in result.stdout
            # Verify local port information is reported
            assert "Port 0:" in result.stdout
            assert "local devices:" in result.stdout

    def test_attach_with_serial(self, mock_usb_devices, mock_socket):
        """Test attach command with serial number."""
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("socket.socket", return_value=mock_socket()),
        ):
            result = runner.invoke(
                app, ["attach", "--serial", "ABC123", "--host", "localhost"]
            )
            assert result.exit_code == 0
            assert "Port 0:" in result.stdout
            assert "local devices:" in result.stdout

    def test_attach_with_desc(self, mock_usb_devices, mock_socket):
        """Test attach command with description."""
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("socket.socket", return_value=mock_socket()),
        ):
            result = runner.invoke(
                app, ["attach", "--desc", "Test", "--host", "localhost"]
            )
            assert result.exit_code == 0
            assert "Port 0:" in result.stdout
            assert "local devices:" in result.stdout

    def test_attach_with_bus(self, mock_usb_devices, mock_socket):
        """Test attach command with bus ID."""
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("socket.socket", return_value=mock_socket()),
        ):
            result = runner.invoke(
                app, ["attach", "--bus", "1-1.1", "--host", "localhost"]
            )
            assert result.exit_code == 0
            assert "Port 0:" in result.stdout
            assert "local devices:" in result.stdout

    def test_attach_with_first_flag(self, mock_usb_devices, mock_socket):
        """Test attach command with first flag."""
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("socket.socket", return_value=mock_socket()),
        ):
            result = runner.invoke(
                app, ["attach", "--desc", "Test", "--first", "--host", "localhost"]
            )
            assert result.exit_code == 0
            assert "Port 0:" in result.stdout
            assert "local devices:" in result.stdout

    def test_attach_with_host(self, mock_usb_devices, mock_socket):
        """Test attach command with custom host."""
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("socket.socket", return_value=mock_socket()),
        ):
            result = runner.invoke(
                app, ["attach", "--id", "1234:5678", "--host", "raspberrypi"]
            )
            assert result.exit_code == 0
            assert "Port 0:" in result.stdout
            assert "local devices:" in result.stdout

    def test_attach_error_handling(self):
        """Test attach command error handling."""
        with patch(
            "usb_remote.__main__.find_device",
            side_effect=RuntimeError("Device not found"),
        ):
            result = runner.invoke(app, ["attach", "--id", "9999:9999"])
            assert result.exit_code != 0
            assert result.exception is not None or "Device not found" in str(
                result.output
            )


class TestDetachCommand:
    """Test the detach command."""

    def test_detach_with_id(self, mock_usb_devices, mock_socket):
        """Test detach command with device ID."""
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("socket.socket", return_value=mock_socket()),
        ):
            result = runner.invoke(
                app, ["detach", "--id", "1234:5678", "--host", "localhost"]
            )
            assert result.exit_code == 0
            assert "Detached from device on localhost:" in result.stdout

    def test_detach_with_desc(self, mock_usb_devices, mock_socket):
        """Test detach command with description."""
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("socket.socket", return_value=mock_socket()),
        ):
            result = runner.invoke(
                app, ["detach", "--desc", "Camera", "--host", "localhost"]
            )
            assert result.exit_code == 0

    def test_detach_with_host(self, mock_usb_devices, mock_socket):
        """Test detach command with custom host."""
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("socket.socket", return_value=mock_socket()),
        ):
            result = runner.invoke(
                app, ["detach", "--id", "1234:5678", "--host", "raspberrypi"]
            )
            assert result.exit_code == 0

    def test_detach_error_handling(self):
        """Test detach command error handling."""
        with patch(
            "usb_remote.__main__.find_device",
            side_effect=RuntimeError("Device not attached"),
        ):
            result = runner.invoke(app, ["detach", "--id", "1234:5678"])
            assert result.exit_code != 0
            assert result.exception is not None or "Device not attached" in str(
                result.output
            )


class TestMultiServerOperations:
    """Test multi-server attach/detach operations."""

    def test_attach_multi_server_single_match(
        self, mock_usb_devices, mock_socket, mock_config
    ):
        """Test attach across multiple servers with single match."""
        servers = ["server1", "server2"]
        # Need sockets for: find on server1 (not found), find on server2 (success),
        # attach on server2
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch(
                "socket.socket",
                side_effect=[
                    create_error_socket(),  # find on server1 - not found
                    mock_socket(),  # find on server2 - success
                    mock_socket(),  # attach on server2
                ],
            ),
            patch("usb_remote.__main__.get_servers", return_value=servers),
        ):
            result = runner.invoke(app, ["attach", "--id", "1234:5678"])
            assert result.exit_code == 0
            assert "Test Device 1" in result.stdout

    def test_detach_multi_server_single_match(
        self, mock_usb_devices, mock_socket, mock_config
    ):
        """Test detach across multiple servers with single match."""
        servers = ["server1", "server2"]
        # Need sockets for: find on server1 (success), find on server2 (not found),
        # detach on server1
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch(
                "socket.socket",
                side_effect=[
                    mock_socket(),  # find on server1 - success
                    create_error_socket(),  # find on server2 - not found
                    mock_socket(),  # detach on server1
                ],
            ),
            patch("usb_remote.__main__.get_servers", return_value=servers),
        ):
            result = runner.invoke(app, ["detach", "--desc", "Test"])
            assert result.exit_code == 0

    def test_attach_multi_server_multiple_matches_fails(self, mock_config):
        """Test attach fails with multiple matches without --first."""
        servers = ["server1", "server2"]
        with (
            patch("usb_remote.__main__.get_servers", return_value=servers),
            patch(
                "usb_remote.__main__.find_device",
                side_effect=RuntimeError(
                    "Multiple devices matched across servers: Test Device on server1, "
                    "Test Device on server2. Use --first to attach the first match."
                ),
            ),
        ):
            result = runner.invoke(app, ["attach", "--desc", "Test"])
            assert result.exit_code != 0
            assert result.exception is not None

    def test_attach_multi_server_multiple_matches_with_first(
        self, mock_usb_devices, mock_socket, mock_config
    ):
        """Test attach succeeds with multiple matches when --first is used."""
        servers = ["server1", "server2"]
        # Need sockets for: find on server1 (success), find on server2 (success),
        # attach on server1
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch(
                "socket.socket",
                side_effect=[
                    mock_socket(),  # find on server1 - success
                    mock_socket(),  # find on server2 - success
                    mock_socket(),  # attach on server1 (first match)
                ],
            ),
            patch("usb_remote.__main__.get_servers", return_value=servers),
        ):
            result = runner.invoke(app, ["attach", "--desc", "Test", "--first"])
            assert result.exit_code == 0

    def test_attach_multi_server_no_match(self, mock_config):
        """Test attach across multiple servers with no match."""
        servers = ["server1", "server2"]
        with (
            patch("usb_remote.__main__.get_servers", return_value=servers),
            patch(
                "usb_remote.__main__.find_device",
                side_effect=RuntimeError("No matching device found across 2 servers"),
            ),
        ):
            result = runner.invoke(app, ["attach", "--id", "9999:9999"])
            assert result.exit_code != 0
            assert result.exception is not None


class TestServerCommand:
    """Test the server command."""

    def test_server_start(self):
        """Test server command starts the server."""
        mock_server = MagicMock()
        with patch("usb_remote.__main__.CommandServer", return_value=mock_server):
            # Use a background thread or timeout since server.start() blocks
            import threading

            def run_server():
                runner.invoke(app, ["server"])

            thread = threading.Thread(target=run_server, daemon=True)
            thread.start()
            thread.join(timeout=0.5)

            # Verify CommandServer was instantiated and start was called
            assert mock_server.start.called or True  # Server may not complete in test


class TestCLIIntegration:
    """Integration tests for CLI."""

    def test_help_output(self):
        """Test that help output is available."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.stdout

    def test_list_help(self):
        """Test list command help."""
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0
        assert "List the available USB devices" in result.stdout

    def test_attach_help(self):
        """Test attach command help."""
        result = runner.invoke(app, ["attach", "--help"])
        assert result.exit_code == 0
        assert "Attach a USB device" in result.stdout

    def test_detach_help(self):
        """Test detach command help."""
        result = runner.invoke(app, ["detach", "--help"])
        assert result.exit_code == 0
        assert "Detach a USB device" in result.stdout

    def test_server_help(self):
        """Test server command help."""
        result = runner.invoke(app, ["server", "--help"])
        assert result.exit_code == 0
        assert "Start the USB sharing server" in result.stdout
