"""Utility functions for subprocess operations."""

import logging
import subprocess

from usb_remote.config import get_servers

logger = logging.getLogger(__name__)


def get_host_list(host: str | None) -> list[str]:
    """Get list of server hosts from argument or config."""
    if host:
        servers = [host]
    else:
        servers = get_servers()
    if not servers:
        logger.warning("No servers configured, defaulting to localhost")
        servers = ["localhost"]
    return servers


def run_command(
    command: list[str],
    capture_output: bool = True,
    text: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """
    Run a command using subprocess.run with common defaults.

    Args:
        command: The command and its arguments as a list of strings
        capture_output: Whether to capture stdout and stderr
        text: Whether to return output as text (string) instead of bytes
        check: Whether to raise CalledProcessError on non-zero exit

    Returns:
        CompletedProcess instance containing the result

    Raises:
        CalledProcessError: If check=True and the command returns non-zero
    """
    try:
        logger.debug(f"Running command: {' '.join(command)}")
        result = subprocess.run(
            command,
            capture_output=capture_output,
            text=text,
            check=check,
        )
        logger.debug(f"Command completed with exit code {result.returncode}")
        return result
    except subprocess.CalledProcessError as e:
        cmd_str = " ".join(command)
        logger.error(f"Command '{cmd_str}' failed with exit code {e.returncode}")
        logger.error(f"Stdout: {e.stdout}")
        logger.error(f"Stderr: {e.stderr}")
        raise RuntimeError(e.stderr) from e
