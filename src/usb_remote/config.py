"""Configuration management for usb_remote."""

import logging
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "usb-remote" / "usb-remote.config"
SYSTEMD_CONFIG_PATH = Path("/etc/usb-remote-client/usb-remote.config")
DEFAULT_TIMEOUT = 5.0

SERVER_PORT = 5055


class UsbRemoteConfig(BaseModel):
    """Pydantic model for usb_remote configuration."""

    servers: list[str] = Field(default_factory=list)
    server_ranges: list[str] = Field(default_factory=list)
    timeout: float = Field(default=DEFAULT_TIMEOUT, gt=0)
    server_port: int = Field(default=SERVER_PORT)
    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_file(cls, config_path: Path) -> "UsbRemoteConfig":
        """
        Load configuration from a YAML file.

        Args:
            config_path: Path to the config file.

        Returns:
            UsbRemoteConfig instance with values from file or defaults.
        """
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f)

            if data is None:
                logger.debug(f"Empty config file: {config_path}")
                return cls()

            logger.debug(f"Loaded config from {config_path}")
            return cls(**data)

        except FileNotFoundError:
            logger.debug(f"Config file not found: {config_path}")
            return cls()
        except Exception as e:
            logger.error(f"Error reading config file {config_path}: {e}")
            return cls()

    def to_file(self) -> None:
        """
        Save configuration to a YAML file.

        Args:
            config_path: Path to the config file.
        """
        config_path = discover_config_path() or DEFAULT_CONFIG_PATH
        # Create directory if it doesn't exist
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(config_path, "w") as f:
                yaml.safe_dump(
                    self.model_dump(exclude_defaults=False),
                    f,
                    default_flow_style=False,
                )
            logger.debug(f"Saved config to {config_path}")
        except Exception as e:
            logger.error(f"Error writing config file {config_path}: {e}")
            raise


def discover_config_path() -> Path | None:
    """
    Discover config file path using the following priority:
    1. Environment variable USB_REMOTE_CONFIG
    2. /etc/usb-remote-client/usb-remote-client.config (if running as systemd service)
    3. Local .usb-remote.config in current directory
    4. Default ~/.config/usb_remote/usb-remote.config

    Returns:
        Path to config file if found, None otherwise.
    """
    # 1. Check environment variable
    env_config = os.environ.get("USB_REMOTE_CONFIG")
    if env_config:
        env_path = Path(env_config).expanduser()
        if env_path.exists():
            logger.debug(f"Using config from USB_REMOTE_CONFIG: {env_path}")
            return env_path
        else:
            logger.warning(f"USB_REMOTE_CONFIG points to non-existent file: {env_path}")

    # 2. Check systemd config (when running as systemd service)
    if os.environ.get("INVOCATION_ID") and SYSTEMD_CONFIG_PATH.exists():
        logger.debug(f"Using systemd config: {SYSTEMD_CONFIG_PATH}")
        return SYSTEMD_CONFIG_PATH

    # 3. Check local directory
    local_config = Path.cwd() / ".usb-remote.config"
    if local_config.exists():
        logger.debug(f"Using local config: {local_config}")
        return local_config

    # 3. Check default location
    if DEFAULT_CONFIG_PATH.exists():
        logger.debug(f"Using default config: {DEFAULT_CONFIG_PATH}")
        return DEFAULT_CONFIG_PATH

    logger.debug("No config file found")
    return None


def get_config() -> UsbRemoteConfig:
    """
    Load configuration from file.

    Args:
        config_path: Path to config file. If None, discovers using:
            1. USB_REMOTE_CONFIG environment variable
            2. .usb-remote.config in current directory
            3. ~/.config/usb_remote/usb-remote.config (default)

    Returns:
        UsbRemoteConfig instance with values from file or defaults.
    """
    config_path = discover_config_path()

    if config_path is None:
        logger.debug("No config file found, using defaults")
        return UsbRemoteConfig()

    return UsbRemoteConfig.from_file(config_path)


def get_servers(config_path: Path | None = None) -> list[str]:
    """
    Read list of server addresses from config file.

    Args:
        config_path: Path to config file. If None, discovers automatically.

    Returns:
        List of server hostnames/IPs. Returns empty list if file doesn't exist.
    """
    config = get_config()
    logger.debug(f"Loaded {len(config.servers)} servers from config")
    return config.servers


def get_server_ranges() -> list[str]:
    """
    Read list of server IP ranges from config file.

    Returns:
        List of IP ranges (e.g., ['192.168.1.30-192.168.1.40']).
        Returns empty list if not configured.
    """
    config = get_config()
    logger.debug(f"Loaded {len(config.server_ranges)} server ranges from config")
    return config.server_ranges


def get_timeout() -> float:
    """
    Read connection timeout from config file.

    Args:
        config_path: Path to config file. If None, discovers automatically.

    Returns:
        Timeout in seconds. Returns default if not configured.
    """
    config = get_config()
    logger.debug(f"Using timeout: {config.timeout}s")
    return config.timeout


def get_server_port() -> int:
    """
    Read server port from config file.

    Returns:
        Server port number. Returns default if not configured.
    """
    config = get_config()
    return config.server_port


def save_servers(servers: list[str]) -> None:
    """
    Save list of server addresses to config file.

    Args:
        servers: List of server hostnames/IPs
        config_path: Path to config file. If None, uses default location.
    """
    # Load existing config to preserve other settings
    config = get_config()
    config.servers = servers
    config.to_file()
