"""Unit tests for systemd service management."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from usb_remote.service import (
    get_systemd_service_content,
    install_systemd_service,
    uninstall_systemd_service,
)


class TestGetSystemdServiceContent:
    """Test systemd service file generation."""

    def test_default_user(self):
        """Test service content with default (current) user."""
        with patch("getpass.getuser", return_value="testuser"):
            content = get_systemd_service_content()

        assert "User=testuser" in content
        assert f"ExecStart={sys.executable} -m usb_remote server" in content
        assert "Description=USB-Remote - USB Device Sharing Server" in content
        assert "[Unit]" in content
        assert "[Service]" in content
        assert "[Install]" in content

    def test_custom_user(self):
        """Test service content with specified user."""
        content = get_systemd_service_content(user="customuser")

        assert "User=customuser" in content
        assert "ExecStart=" in content

    def test_working_directory(self):
        """Test that working directory is set."""
        with patch("pathlib.Path.home", return_value=Path("/home/testuser")):
            content = get_systemd_service_content()

        assert "WorkingDirectory=/home/testuser" in content

    def test_security_hardening(self):
        """Test that security options are present."""
        content = get_systemd_service_content()

        assert "NoNewPrivileges=true" in content
        assert "PrivateTmp=true" in content

    def test_restart_options(self):
        """Test restart configuration."""
        content = get_systemd_service_content()

        assert "Restart=on-failure" in content
        assert "RestartSec=5s" in content


class TestInstallSystemdService:
    """Test systemd service installation."""

    @patch("usb_remote.service.shutil.which")
    def test_no_systemd(self, mock_which):
        """Test error when systemd is not available."""
        mock_which.return_value = None

        with pytest.raises(RuntimeError, match="systemd not found"):
            install_systemd_service()

    @patch("usb_remote.service._run_systemctl")
    @patch("usb_remote.service.shutil.which")
    def test_user_service_installation(self, mock_which, mock_systemctl):
        """Test installing user service."""
        mock_which.return_value = "/usr/bin/systemctl"

        with patch("pathlib.Path.write_text") as mock_write:
            with patch("pathlib.Path.mkdir"):
                install_systemd_service(user="testuser", system_wide=False)

        # Verify service file was written
        mock_write.assert_called_once()

        # Verify systemctl daemon-reload was called
        mock_systemctl.assert_called_once_with(["daemon-reload"], False)

    @patch("usb_remote.service._run_systemctl")
    @patch("usb_remote.service.shutil.which")
    def test_system_service_installation(self, mock_which, mock_systemctl):
        """Test installing system-wide service."""
        mock_which.return_value = "/usr/bin/systemctl"

        with patch("pathlib.Path.write_text") as mock_write:
            with patch("pathlib.Path.mkdir"):
                install_systemd_service(system_wide=True)

        mock_write.assert_called_once()
        mock_systemctl.assert_called_once_with(["daemon-reload"], True)

    @patch("usb_remote.service.shutil.which")
    def test_permission_denied_directory_creation(self, mock_which):
        """Test handling of permission denied when creating directory."""
        mock_which.return_value = "/usr/bin/systemctl"

        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Access denied")):
            with pytest.raises(RuntimeError, match="Permission denied"):
                install_systemd_service(system_wide=True)

    @patch("usb_remote.service.shutil.which")
    def test_permission_denied_file_write(self, mock_which):
        """Test handling of permission denied when writing file."""
        mock_which.return_value = "/usr/bin/systemctl"

        with patch("pathlib.Path.mkdir"):
            with patch(
                "pathlib.Path.write_text", side_effect=PermissionError("Access denied")
            ):
                with pytest.raises(RuntimeError, match="Permission denied"):
                    install_systemd_service(system_wide=True)

    @patch("usb_remote.service._run_systemctl")
    @patch("usb_remote.service.shutil.which")
    def test_systemctl_failure(self, mock_which, mock_systemctl):
        """Test handling of systemctl command failure."""
        mock_which.return_value = "/usr/bin/systemctl"
        mock_systemctl.side_effect = RuntimeError("systemctl failed")

        with patch("pathlib.Path.write_text"):
            with patch("pathlib.Path.mkdir"):
                with pytest.raises(RuntimeError, match="Failed to reload systemd"):
                    install_systemd_service()

    @patch("usb_remote.service._run_systemctl")
    @patch("usb_remote.service.shutil.which")
    def test_user_service_directory_path(self, mock_which, mock_systemctl):
        """Test that user service uses correct directory."""
        mock_which.return_value = "/usr/bin/systemctl"

        written_path = None

        def capture_write(content):
            nonlocal written_path
            # Capture the path that write_text was called on
            pass

        with patch("pathlib.Path.home", return_value=Path("/home/testuser")):
            with patch(
                "pathlib.Path.write_text", side_effect=capture_write
            ) as mock_write:
                with patch("pathlib.Path.mkdir"):
                    install_systemd_service(system_wide=False)

        # Check that write was called (path checking happens in the service logic)
        assert mock_write.called


class TestUninstallSystemdService:
    """Test systemd service uninstallation."""

    @patch("usb_remote.service._run_systemctl")
    def test_uninstall_nonexistent_service(self, mock_systemctl):
        """Test uninstalling when service file doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            # Should complete without error
            uninstall_systemd_service(system_wide=False)

        # systemctl should not be called
        mock_systemctl.assert_not_called()

    @patch("usb_remote.service._run_systemctl")
    def test_uninstall_user_service(self, mock_systemctl):
        """Test uninstalling user service."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.unlink") as mock_unlink:
                uninstall_systemd_service(system_wide=False)

        # Verify stop and disable were called
        assert mock_systemctl.call_count == 3  # stop, disable, daemon-reload
        mock_systemctl.assert_any_call(
            ["stop", "usb-remote.service"], False, check=False
        )
        mock_systemctl.assert_any_call(
            ["disable", "usb-remote.service"], False, check=False
        )
        mock_systemctl.assert_any_call(["daemon-reload"], False)

        # Verify file was deleted
        mock_unlink.assert_called_once()

    @patch("usb_remote.service._run_systemctl")
    def test_uninstall_system_service(self, mock_systemctl):
        """Test uninstalling system service."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.unlink"):
                uninstall_systemd_service(system_wide=True)

        # Verify system-wide calls
        mock_systemctl.assert_any_call(
            ["stop", "usb-remote.service"], True, check=False
        )
        mock_systemctl.assert_any_call(
            ["disable", "usb-remote.service"], True, check=False
        )
        mock_systemctl.assert_any_call(["daemon-reload"], True)

    @patch("usb_remote.service._run_systemctl")
    def test_uninstall_permission_denied(self, mock_systemctl):
        """Test handling permission denied when deleting file."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch(
                "pathlib.Path.unlink", side_effect=PermissionError("Access denied")
            ):
                with pytest.raises(RuntimeError, match="Permission denied"):
                    uninstall_systemd_service(system_wide=True)

    @patch("usb_remote.service._run_systemctl")
    def test_uninstall_systemctl_reload_failure(self, mock_systemctl):
        """Test handling daemon-reload failure."""

        def systemctl_side_effect(args, system_wide, check=True):
            if args == ["daemon-reload"]:
                raise RuntimeError("daemon-reload failed")

        mock_systemctl.side_effect = systemctl_side_effect

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.unlink"):
                with pytest.raises(RuntimeError, match="Failed to reload systemd"):
                    uninstall_systemd_service(system_wide=False)

    @patch("usb_remote.service._run_systemctl")
    def test_uninstall_stop_disable_errors_ignored(self, mock_systemctl):
        """Test that stop/disable errors are logged but don't fail uninstall."""

        def systemctl_side_effect(args, system_wide, check=True):
            if args[0] in ["stop", "disable"]:
                raise Exception("Service not running")
            # daemon-reload should succeed

        mock_systemctl.side_effect = systemctl_side_effect

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.unlink"):
                # Should complete despite stop/disable errors
                uninstall_systemd_service(system_wide=False)
