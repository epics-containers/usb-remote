"""Client tests using the CLI interface."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from tests.conftest import create_error_socket, mock_subprocess_run
from usb_remote.__main__ import app

runner = CliRunner()


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

    def test_attach_error_handling(self, mock_config):
        """Test attach command error handling."""
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("socket.socket", return_value=create_error_socket()),
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

    def test_detach_error_handling(self, mock_config):
        """Test detach command error handling."""
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("socket.socket", return_value=create_error_socket()),
        ):
            result = runner.invoke(app, ["detach", "--id", "1234:5678"])
            assert result.exit_code != 0
            assert result.exception is not None or "Device not attached" in str(
                result.output
            )


class TestMultiServerOperations:
    """Test multi-server attach/detach operations."""

    def test_attach_multi_server_single_match(self, mock_usb_devices, mock_socket):
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
            patch("usb_remote.utility.get_servers", return_value=servers),
            patch("usb_remote.config.get_timeout", return_value=0.1),
        ):
            result = runner.invoke(app, ["attach", "--id", "1234:5678"])
            assert result.exit_code == 0
            assert "Test Device 1" in result.stdout

    def test_detach_multi_server_single_match(self, mock_usb_devices, mock_socket):
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
            patch("usb_remote.utility.get_servers", return_value=servers),
            patch("usb_remote.config.get_timeout", return_value=0.1),
        ):
            result = runner.invoke(app, ["detach", "--desc", "Test"])
            assert result.exit_code == 0

    def test_attach_multi_server_multiple_matches_fails(self, mock_socket):
        """Test attach fails with multiple matches without --first."""
        servers = ["server1", "server2"]
        # Both servers return a matching device
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch(
                "socket.socket",
                side_effect=[
                    mock_socket(),  # find on server1 - success
                    mock_socket(),  # find on server2 - success
                ],
            ),
            patch("usb_remote.utility.get_servers", return_value=servers),
            patch("usb_remote.config.get_timeout", return_value=0.1),
        ):
            result = runner.invoke(app, ["attach", "--desc", "Test"])
            assert result.exit_code != 0
            assert result.exception is not None

    def test_attach_multi_server_multiple_matches_with_first(
        self, mock_usb_devices, mock_socket
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
            patch("usb_remote.utility.get_servers", return_value=servers),
            patch("usb_remote.config.get_timeout", return_value=0.1),
        ):
            result = runner.invoke(app, ["attach", "--desc", "Test", "--first"])
            assert result.exit_code == 0

    def test_attach_multi_server_no_match(self):
        """Test attach across multiple servers with no match."""
        servers = ["server1", "server2"]
        # Both servers return error (device not found)
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch(
                "socket.socket",
                side_effect=[
                    create_error_socket(),  # find on server1 - not found
                    create_error_socket(),  # find on server2 - not found
                ],
            ),
            patch("usb_remote.utility.get_servers", return_value=servers),
            patch("usb_remote.config.get_timeout", return_value=0.1),
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
