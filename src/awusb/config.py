"""Configuration management for awusb."""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "awusb" / "awusb.config"
DEFAULT_TIMEOUT = 5.0


def get_servers(config_path: Path | None = None) -> list[str]:
    """
    Read list of server addresses from config file.

    Args:
        config_path: Path to config file. If None, uses default location.

    Returns:
        List of server hostnames/IPs. Returns empty list if file doesn't exist.
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    if not config_path.exists():
        logger.debug(f"Config file not found: {config_path}")
        return []

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        if config is None:
            logger.debug(f"Empty config file: {config_path}")
            return []

        servers = config.get("servers", [])
        if not isinstance(servers, list):
            logger.warning(f"Invalid servers config in {config_path}, expected list")
            return []

        logger.debug(f"Loaded {len(servers)} servers from config")
        return servers

    except Exception as e:
        logger.error(f"Error reading config file {config_path}: {e}")
        return []


def get_timeout(config_path: Path | None = None) -> float:
    """
    Read connection timeout from config file.

    Args:
        config_path: Path to config file. If None, uses default location.

    Returns:
        Timeout in seconds. Returns default if not configured.
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    if not config_path.exists():
        return DEFAULT_TIMEOUT

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        if config is None:
            return DEFAULT_TIMEOUT

        timeout = config.get("timeout", DEFAULT_TIMEOUT)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            logger.warning(f"Invalid timeout config in {config_path}, using default")
            return DEFAULT_TIMEOUT

        logger.debug(f"Using timeout: {timeout}s")
        return float(timeout)

    except Exception as e:
        logger.error(f"Error reading config file {config_path}: {e}")
        return DEFAULT_TIMEOUT


def save_servers(servers: list[str], config_path: Path | None = None) -> None:
    """
    Save list of server addresses to config file.

    Args:
        servers: List of server hostnames/IPs
        config_path: Path to config file. If None, uses default location.
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config = {"servers": servers}

    try:
        with open(config_path, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)
        logger.debug(f"Saved {len(servers)} servers to {config_path}")
    except Exception as e:
        logger.error(f"Error writing config file {config_path}: {e}")
        raise
