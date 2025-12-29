"""
System-level CLI tests using real command execution with mocked USB/IP.

These tests use the same subprocess mocks as test_system_integration
but test the CLI commands directly.
"""

from unittest.mock import patch

from typer.testing import CliRunner

from usb_remote.__main__ import app
from usb_remote.config import UsbRemoteConfig

runner = CliRunner()


class TestSystemCLI:
    """Test CLI commands with system-level mocks."""

    def test_list_command(self, mock_subprocess_run, server_port, server_instance):
        """Test the list command with mocked USB devices."""
        # Mock config to use our test server
        test_config = UsbRemoteConfig(
            servers=["127.0.0.1"], server_port=server_port, timeout=0.5
        )
        with patch("usb_remote.config.get_config", return_value=test_config):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        # Should show devices from the mock
        assert "2e8a:000a" in result.stdout
        assert "Raspberry Pi" in result.stdout

    def test_list_with_server_option(
        self, mock_subprocess_run, server_port, server_instance
    ):
        """Test list command with explicit server."""
        test_config = UsbRemoteConfig(server_port=server_port, timeout=0.5)
        with patch("usb_remote.config.get_config", return_value=test_config):
            result = runner.invoke(app, ["list", "--host", "127.0.0.1"])

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "2e8a:000a" in result.stdout

    def test_attach_command_with_busid(
        self, mock_subprocess_run, server_port, server_instance
    ):
        """Test attach command with bus ID."""
        test_config = UsbRemoteConfig(server_port=server_port, timeout=0.5)
        with patch("usb_remote.config.get_config", return_value=test_config):
            result = runner.invoke(
                app, ["attach", "--bus", "1-1.1", "--host", "127.0.0.1"]
            )

        # The command should succeed
        assert result.exit_code == 0

        # Verify subprocess.run was called for bind and attach
        bind_calls = [
            call
            for call in mock_subprocess_run.call_args_list
            if len(call.args) > 0
            and len(call.args[0]) > 2
            and call.args[0][0] == "sudo"
            and call.args[0][1] == "usbip"
            and call.args[0][2] == "bind"
        ]
        assert len(bind_calls) >= 1, "Should have called usbip bind"

    def test_attach_command_with_vendor_product(
        self, mock_subprocess_run, server_port, server_instance
    ):
        """Test attach command with vendor and product IDs."""
        test_config = UsbRemoteConfig(server_port=server_port, timeout=0.5)
        with patch("usb_remote.config.get_config", return_value=test_config):
            result = runner.invoke(
                app, ["attach", "--id", "2e8a:000a", "--host", "127.0.0.1"]
            )

        # The command should succeed
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

    def test_detach_command(self, mock_subprocess_run, server_port, server_instance):
        """Test detach command after attaching a device."""
        test_config = UsbRemoteConfig(server_port=server_port, timeout=0.5)
        with patch("usb_remote.config.get_config", return_value=test_config):
            # First attach a device
            attach_result = runner.invoke(
                app, ["attach", "--bus", "1-1.1", "--host", "127.0.0.1"]
            )
            assert attach_result.exit_code == 0

            # Now detach it
            detach_result = runner.invoke(
                app, ["detach", "--bus", "1-1.1", "--host", "127.0.0.1"]
            )

        # The command should succeed
        assert detach_result.exit_code == 0

        # Verify subprocess.run was called for unbind and detach
        unbind_calls = [
            call
            for call in mock_subprocess_run.call_args_list
            if len(call.args) > 0
            and len(call.args[0]) > 2
            and call.args[0][0] == "sudo"
            and call.args[0][1] == "usbip"
            and call.args[0][2] == "unbind"
        ]
        assert len(unbind_calls) >= 1, "Should have called usbip unbind"

        detach_calls = [
            call
            for call in mock_subprocess_run.call_args_list
            if len(call.args) > 0
            and len(call.args[0]) > 2
            and call.args[0][0] == "sudo"
            and call.args[0][1] == "usbip"
            and call.args[0][2] == "detach"
        ]
        assert len(detach_calls) >= 1, "Should have called usbip detach"

    def test_list_ports_command(
        self, mock_subprocess_run, server_port, server_instance
    ):
        """Test ports command."""
        test_config = UsbRemoteConfig(server_port=server_port, timeout=0.5)
        with patch("usb_remote.config.get_config", return_value=test_config):
            # First attach a device so there's something to list
            attach_result = runner.invoke(
                app, ["attach", "--bus", "1-1.1", "--host", "127.0.0.1"]
            )
            assert attach_result.exit_code == 0

            # Now list ports
            result = runner.invoke(app, ["ports"])

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        # Should show the attached device
        assert "Port" in result.stdout

    def test_find_command(self, mock_subprocess_run, server_port, server_instance):
        """Test find command with vendor/product IDs."""
        test_config = UsbRemoteConfig(server_port=server_port, timeout=0.5)
        with patch("usb_remote.config.get_config", return_value=test_config):
            result = runner.invoke(
                app, ["find", "--id", "2e8a:000a", "--host", "127.0.0.1"]
            )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "1-1.1" in result.stdout
        assert "2e8a:000a" in result.stdout

    def test_list_local_command(self, mock_subprocess_run):
        """Test list command with --local flag."""
        result = runner.invoke(app, ["list", "--local"])

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        # Should show locally connected devices from mocked lsusb
        assert "2e8a:000a" in result.stdout

    def test_config_show_command(self, mock_subprocess_run, tmp_path):
        """Test config show command."""
        # Create a temporary config file
        config_file = tmp_path / "usb-remote.config"
        test_config = UsbRemoteConfig(
            servers=["192.168.1.100", "server2.local"], timeout=5.0
        )

        # Patch discover_config_path to return our temp file
        with patch(
            "usb_remote.__main__.discover_config_path", return_value=str(config_file)
        ):
            with patch("usb_remote.__main__.get_config", return_value=test_config):
                result = runner.invoke(app, ["config", "show"])

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "192.168.1.100" in result.stdout
        assert "server2.local" in result.stdout
        assert "5.0s" in result.stdout

    def test_config_show_no_config(self, mock_subprocess_run):
        """Test config show command with no config file."""
        with patch("usb_remote.__main__.discover_config_path", return_value=None):
            with patch(
                "usb_remote.__main__.get_config", return_value=UsbRemoteConfig()
            ):
                result = runner.invoke(app, ["config", "show"])

        assert result.exit_code == 0
        assert "No configuration file found" in result.stdout
        assert "Default configuration" in result.stdout

    def test_config_add_server_command(self, mock_subprocess_run, tmp_path):
        """Test config add-server command."""
        config_file = tmp_path / "usb-remote.config"
        test_config = UsbRemoteConfig(servers=["existing.server"])

        with patch(
            "usb_remote.__main__.discover_config_path", return_value=str(config_file)
        ):
            with patch("usb_remote.__main__.get_config", return_value=test_config):
                with patch("usb_remote.__main__.save_servers") as mock_save:
                    result = runner.invoke(app, ["config", "add-server", "new.server"])

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "Added server 'new.server'" in result.stdout
        # Verify save_servers was called with updated list
        mock_save.assert_called_once()
        saved_servers = mock_save.call_args[0][0]
        assert "existing.server" in saved_servers
        assert "new.server" in saved_servers

    def test_config_add_server_duplicate(self, mock_subprocess_run, tmp_path):
        """Test config add-server command with duplicate server."""
        config_file = tmp_path / "usb-remote.config"
        test_config = UsbRemoteConfig(servers=["existing.server"])

        with patch(
            "usb_remote.__main__.discover_config_path", return_value=str(config_file)
        ):
            with patch("usb_remote.__main__.get_config", return_value=test_config):
                result = runner.invoke(app, ["config", "add-server", "existing.server"])

        assert result.exit_code == 1
        # use result.output which includes both stdout and stderr
        assert "already in the configuration" in result.output

    def test_config_rm_server_command(self, mock_subprocess_run, tmp_path):
        """Test config rm-server command."""
        config_file = tmp_path / "usb-remote.config"
        test_config = UsbRemoteConfig(servers=["server1", "server2"])

        with patch(
            "usb_remote.__main__.discover_config_path", return_value=str(config_file)
        ):
            with patch("usb_remote.__main__.get_config", return_value=test_config):
                with patch("usb_remote.__main__.save_servers") as mock_save:
                    result = runner.invoke(app, ["config", "rm-server", "server1"])

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "Removed server 'server1'" in result.stdout
        # Verify save_servers was called with updated list
        mock_save.assert_called_once()
        saved_servers = mock_save.call_args[0][0]
        assert "server1" not in saved_servers
        assert "server2" in saved_servers

    def test_config_rm_server_not_found(self, mock_subprocess_run, tmp_path):
        """Test config rm-server command with non-existent server."""
        config_file = tmp_path / "usb-remote.config"
        test_config = UsbRemoteConfig(servers=["server1"])

        with patch(
            "usb_remote.__main__.discover_config_path", return_value=str(config_file)
        ):
            with patch("usb_remote.__main__.get_config", return_value=test_config):
                result = runner.invoke(app, ["config", "rm-server", "server2"])

        assert result.exit_code == 1
        assert "not in the configuration" in result.output

    def test_config_rm_server_no_config_file(self, mock_subprocess_run):
        """Test config rm-server command when no config file exists."""
        with patch("usb_remote.__main__.discover_config_path", return_value=None):
            result = runner.invoke(app, ["config", "rm-server", "server1"])

        assert result.exit_code == 1
        assert "No configuration file found" in result.output

    def test_config_set_timeout_command(self, mock_subprocess_run, tmp_path):
        """Test config set-timeout command."""
        config_file = tmp_path / "usb-remote.config"
        test_config = UsbRemoteConfig(timeout=1.0)

        with patch(
            "usb_remote.__main__.discover_config_path", return_value=str(config_file)
        ):
            with patch("usb_remote.__main__.get_config", return_value=test_config):
                # Mock the to_file method on the config module, not the instance
                with patch("usb_remote.config.UsbRemoteConfig.to_file") as mock_to_file:
                    result = runner.invoke(app, ["config", "set-timeout", "10.5"])

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "Set timeout to 10.5s" in result.stdout
        assert test_config.timeout == 10.5
        mock_to_file.assert_called_once()

    def test_config_set_timeout_invalid(self, mock_subprocess_run):
        """Test config set-timeout command with invalid value."""
        test_config = UsbRemoteConfig(timeout=1.0)
        with patch("usb_remote.__main__.get_config", return_value=test_config):
            result = runner.invoke(app, ["config", "set-timeout", "0"])

        assert result.exit_code == 1
        assert "Timeout must be greater than 0" in result.output

    def test_config_set_timeout_negative(self, mock_subprocess_run):
        """Test config set-timeout command with negative value."""
        test_config = UsbRemoteConfig(timeout=1.0)
        with patch("usb_remote.__main__.get_config", return_value=test_config):
            result = runner.invoke(app, ["config", "set-timeout", "-1.5"])

        # Typer returns exit code 2 for invalid arg types (negative parsed as option)
        # but our validation would return 1 if it parsed correctly
        assert result.exit_code in (1, 2)
        # The error might be from typer's parsing or our validation
        assert (
            "Timeout must be greater than 0" in result.output
            or "Error" in result.output
        )

    def test_find_with_description(
        self, mock_subprocess_run, server_port, server_instance
    ):
        """Test find command with description substring."""
        test_config = UsbRemoteConfig(server_port=server_port, timeout=0.5)
        with patch("usb_remote.config.get_config", return_value=test_config):
            result = runner.invoke(
                app, ["find", "--desc", "Raspberry", "--host", "127.0.0.1"]
            )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "Raspberry Pi" in result.stdout

    def test_attach_with_description(
        self, mock_subprocess_run, server_port, server_instance
    ):
        """Test attach command with description substring."""
        test_config = UsbRemoteConfig(server_port=server_port, timeout=0.5)
        with patch("usb_remote.config.get_config", return_value=test_config):
            result = runner.invoke(
                app, ["attach", "--desc", "Raspberry", "--host", "127.0.0.1", "--first"]
            )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "Attached to device" in result.stdout

    def test_detach_with_id(self, mock_subprocess_run, server_port, server_instance):
        """Test detach command with vendor/product ID."""
        test_config = UsbRemoteConfig(server_port=server_port, timeout=0.5)
        with patch("usb_remote.config.get_config", return_value=test_config):
            # First attach a device
            attach_result = runner.invoke(
                app, ["attach", "--bus", "1-1.1", "--host", "127.0.0.1"]
            )
            assert attach_result.exit_code == 0

            # Now detach it using ID
            detach_result = runner.invoke(
                app, ["detach", "--id", "2e8a:000a", "--host", "127.0.0.1"]
            )

        assert detach_result.exit_code == 0, f"Command failed: {detach_result.stdout}"
        assert "Detached from device" in detach_result.stdout

    def test_version_option(self, mock_subprocess_run):
        """Test --version option."""
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "usb-remote" in result.stdout

    def test_debug_option(self, mock_subprocess_run, server_port, server_instance):
        """Test --debug option."""
        test_config = UsbRemoteConfig(server_port=server_port, timeout=0.5)
        with patch("usb_remote.config.get_config", return_value=test_config):
            result = runner.invoke(app, ["--debug", "list", "--host", "127.0.0.1"])

        assert result.exit_code == 0
        # Debug flag should enable logging but not break functionality
        assert "2e8a:000a" in result.stdout
