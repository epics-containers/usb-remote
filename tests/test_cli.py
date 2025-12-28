"""Tests for basic CLI features."""

import subprocess
import sys

from typer.testing import CliRunner

from usb_remote import __version__
from usb_remote.__main__ import app

runner = CliRunner()


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
