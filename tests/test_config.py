"""Unit tests for configuration management."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from usb_remote.config import (
    DEFAULT_TIMEOUT,
    UsbRemoteConfig,
    discover_config_path,
    get_config,
    get_servers,
    get_timeout,
    save_servers,
)


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file."""
    config_file = tmp_path / "test.config"
    return config_file


@pytest.fixture
def sample_config_content():
    """Sample YAML config content."""
    return """servers:
  - server1.example.com
  - 192.168.1.100
  - raspberrypi.local
timeout: 10.0
"""


class TestUsbRemoteConfig:
    """Test the UsbRemoteConfig Pydantic model."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = UsbRemoteConfig()
        assert config.servers == []
        assert config.timeout == DEFAULT_TIMEOUT

    def test_custom_values(self):
        """Test setting custom values."""
        config = UsbRemoteConfig(
            servers=["server1", "server2"],
            timeout=15.0,
        )
        assert config.servers == ["server1", "server2"]
        assert config.timeout == 15.0

    def test_timeout_validation_positive(self):
        """Test that timeout must be positive."""
        with pytest.raises(ValueError, match="greater than 0"):
            UsbRemoteConfig(timeout=0)

        with pytest.raises(ValueError, match="greater than 0"):
            UsbRemoteConfig(timeout=-5.0)

    def test_from_file_valid(self, temp_config_file, sample_config_content):
        """Test loading config from a valid file."""
        temp_config_file.write_text(sample_config_content)
        config = UsbRemoteConfig.from_file(temp_config_file)

        assert len(config.servers) == 3
        assert "server1.example.com" in config.servers
        assert config.timeout == 10.0

    def test_from_file_empty(self, temp_config_file):
        """Test loading from an empty file."""
        temp_config_file.write_text("")
        config = UsbRemoteConfig.from_file(temp_config_file)

        assert config.servers == []
        assert config.timeout == DEFAULT_TIMEOUT

    def test_from_file_not_found(self, tmp_path):
        """Test loading from a non-existent file."""
        nonexistent = tmp_path / "nonexistent.config"
        config = UsbRemoteConfig.from_file(nonexistent)

        assert config.servers == []
        assert config.timeout == DEFAULT_TIMEOUT

    def test_from_file_invalid_yaml(self, temp_config_file):
        """Test loading from a file with invalid YAML."""
        temp_config_file.write_text("invalid: yaml: content: [")
        config = UsbRemoteConfig.from_file(temp_config_file)

        # Should return defaults on error
        assert config.servers == []
        assert config.timeout == DEFAULT_TIMEOUT

    def test_to_file(self, temp_config_file):
        """Test saving config to file."""
        config = UsbRemoteConfig(
            servers=["server1", "server2"],
            timeout=20.0,
        )

        # Mock discover_config_path to return our temp file
        with patch(
            "usb_remote.config.discover_config_path", return_value=temp_config_file
        ):
            config.to_file()

        # Verify file was created
        assert temp_config_file.exists()

        # Verify content can be loaded back
        loaded_config = UsbRemoteConfig.from_file(temp_config_file)
        assert loaded_config.servers == ["server1", "server2"]
        assert loaded_config.timeout == 20.0

    def test_to_file_creates_directory(self, tmp_path):
        """Test that to_file creates parent directories."""
        nested_path = tmp_path / "nested" / "dir" / "config.yaml"

        config = UsbRemoteConfig(servers=["test"])

        with patch("usb_remote.config.discover_config_path", return_value=nested_path):
            config.to_file()

        assert nested_path.exists()
        assert nested_path.parent.exists()


class TestDiscoverConfigPath:
    """Test config file discovery logic."""

    def test_environment_variable_priority(self, temp_config_file):
        """Test that USB_REMOTE_CONFIG env var takes priority."""
        temp_config_file.write_text("servers: []")

        with patch.dict(os.environ, {"USB_REMOTE_CONFIG": str(temp_config_file)}):
            result = discover_config_path()

        assert result == temp_config_file

    def test_environment_variable_nonexistent(self, tmp_path):
        """Test that nonexistent USB_REMOTE_CONFIG is handled."""
        nonexistent = tmp_path / "nonexistent.config"

        with patch.dict(os.environ, {"USB_REMOTE_CONFIG": str(nonexistent)}):
            with patch("usb_remote.config.Path.cwd", return_value=tmp_path):
                with patch(
                    "usb_remote.config.DEFAULT_CONFIG_PATH", tmp_path / "default"
                ):
                    with patch(
                        "usb_remote.config.SYSTEMD_CONFIG_PATH",
                        tmp_path / "systemd",
                    ):
                        result = discover_config_path()

        # Should skip to next priority (none found)
        assert result is None

    def test_local_directory_priority(self, tmp_path):
        """Test that .usb-remote.config in current directory is found."""
        local_config = tmp_path / ".usb-remote.config"
        local_config.write_text("servers: []")

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "cwd", return_value=tmp_path):
                with patch(
                    "usb_remote.config.SYSTEMD_CONFIG_PATH", tmp_path / "systemd"
                ):
                    result = discover_config_path()

        assert result == local_config

    def test_default_location(self, tmp_path):
        """Test that default config location is used."""
        default_config = tmp_path / ".config" / "usb-remote" / "usb_remote.config"
        default_config.parent.mkdir(parents=True)
        default_config.write_text("servers: []")

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "cwd", return_value=tmp_path):
                with patch("usb_remote.config.DEFAULT_CONFIG_PATH", default_config):
                    with patch(
                        "usb_remote.config.SYSTEMD_CONFIG_PATH",
                        tmp_path / "systemd",
                    ):
                        result = discover_config_path()

        assert result == default_config

    def test_no_config_found(self, tmp_path):
        """Test when no config file is found anywhere."""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "cwd", return_value=tmp_path):
                with patch(
                    "usb_remote.config.DEFAULT_CONFIG_PATH", tmp_path / "nonexistent"
                ):
                    with patch(
                        "usb_remote.config.SYSTEMD_CONFIG_PATH",
                        tmp_path / "systemd",
                    ):
                        result = discover_config_path()

        assert result is None


class TestGetConfig:
    """Test the get_config function."""

    def test_get_config_with_defaults(self):
        """Test getting config when no file exists."""
        with patch("usb_remote.config.discover_config_path", return_value=None):
            config = get_config()

        assert isinstance(config, UsbRemoteConfig)
        assert config.servers == []
        assert config.timeout == DEFAULT_TIMEOUT

    def test_get_config_from_file(self, temp_config_file, sample_config_content):
        """Test getting config from a file."""
        temp_config_file.write_text(sample_config_content)

        with patch(
            "usb_remote.config.discover_config_path", return_value=temp_config_file
        ):
            config = get_config()

        assert len(config.servers) == 3
        assert config.timeout == 10.0


class TestGetServers:
    """Test the get_servers function."""

    def test_get_servers_empty(self):
        """Test getting servers when none are configured."""
        with patch("usb_remote.config.get_config", return_value=UsbRemoteConfig()):
            servers = get_servers()

        assert servers == []

    def test_get_servers_with_values(self):
        """Test getting configured servers."""
        mock_config = UsbRemoteConfig(servers=["server1", "server2", "server3"])

        with patch("usb_remote.config.get_config", return_value=mock_config):
            servers = get_servers()

        assert servers == ["server1", "server2", "server3"]


class TestGetTimeout:
    """Test the get_timeout function."""

    def test_get_timeout_default(self):
        """Test getting default timeout."""
        with patch("usb_remote.config.get_config", return_value=UsbRemoteConfig()):
            timeout = get_timeout()

        assert timeout == DEFAULT_TIMEOUT

    def test_get_timeout_custom(self):
        """Test getting custom timeout."""
        mock_config = UsbRemoteConfig(timeout=30.0)

        with patch("usb_remote.config.get_config", return_value=mock_config):
            timeout = get_timeout()

        assert timeout == 30.0


class TestSaveServers:
    """Test the save_servers function."""

    def test_save_servers_preserves_timeout(self, temp_config_file):
        """Test that saving servers preserves other settings."""
        # Create initial config with custom timeout
        initial_config = UsbRemoteConfig(servers=["old_server"], timeout=25.0)

        with patch(
            "usb_remote.config.discover_config_path", return_value=temp_config_file
        ):
            initial_config.to_file()

            # Save new servers
            save_servers(["new_server1", "new_server2"])

        # Verify servers were updated and timeout preserved
        loaded_config = UsbRemoteConfig.from_file(temp_config_file)
        assert loaded_config.servers == ["new_server1", "new_server2"]
        assert loaded_config.timeout == 25.0

    def test_save_servers_creates_file(self, tmp_path):
        """Test that save_servers creates a new config file."""
        config_file = tmp_path / "new_config.yaml"

        with patch("usb_remote.config.discover_config_path", return_value=config_file):
            save_servers(["server1", "server2"])

        assert config_file.exists()
        loaded_config = UsbRemoteConfig.from_file(config_file)
        assert loaded_config.servers == ["server1", "server2"]

    def test_save_empty_servers(self, temp_config_file):
        """Test saving an empty server list."""
        with patch(
            "usb_remote.config.discover_config_path", return_value=temp_config_file
        ):
            save_servers([])

        loaded_config = UsbRemoteConfig.from_file(temp_config_file)
        assert loaded_config.servers == []
