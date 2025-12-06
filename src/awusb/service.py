"""Systemd service installation utilities."""

import logging
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

SYSTEMD_SERVICE_TEMPLATE = """[Unit]
Description=AWUSB - USB Device Sharing Server
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={working_dir}
ExecStart={executable} -m awusb server
Restart=on-failure
RestartSec=5s

# Security hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
"""


def get_systemd_service_content(user: str | None = None) -> str:
    """
    Generate systemd service file content.

    Args:
        user: Username to run the service as. If None, uses current user.

    Returns:
        String content of the systemd service file.
    """
    import getpass
    import os

    if user is None:
        user = getpass.getuser()

    # Get the Python executable path
    executable = sys.executable

    # Use home directory as working directory
    working_dir = str(Path.home())

    return SYSTEMD_SERVICE_TEMPLATE.format(
        user=user, working_dir=working_dir, executable=executable
    )


def install_systemd_service(user: str | None = None, system_wide: bool = False) -> None:
    """
    Install the awusb server as a systemd service.

    Args:
        user: Username to run the service as. If None, uses current user.
        system_wide: If True, install as system service (requires root).
                    If False, install as user service.

    Raises:
        RuntimeError: If installation fails.
    """
    # Check if systemd is available
    if not shutil.which("systemctl"):
        raise RuntimeError("systemd not found. This command requires systemd.")

    service_content = get_systemd_service_content(user)

    if system_wide:
        service_dir = Path("/etc/systemd/system")
        service_name = "awusb.service"
    else:
        service_dir = Path.home() / ".config" / "systemd" / "user"
        service_name = "awusb.service"

    service_path = service_dir / service_name

    # Create directory if it doesn't exist
    try:
        service_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        if system_wide:
            raise RuntimeError(
                "Permission denied. Run with sudo for system-wide installation."
            )
        raise

    # Write service file
    try:
        service_path.write_text(service_content)
        logger.info(f"Service file written to {service_path}")
    except PermissionError:
        if system_wide:
            raise RuntimeError(
                "Permission denied. Run with sudo for system-wide installation."
            )
        raise

    # Reload systemd
    import subprocess

    try:
        if system_wide:
            subprocess.run(
                ["systemctl", "daemon-reload"], check=True, capture_output=True
            )
            logger.info("System service installed successfully!")
            logger.info(f"Enable with: sudo systemctl enable {service_name}")
            logger.info(f"Start with: sudo systemctl start {service_name}")
            logger.info(f"Status: sudo systemctl status {service_name}")
        else:
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=True,
                capture_output=True,
            )
            logger.info("User service installed successfully!")
            logger.info(f"Enable with: systemctl --user enable {service_name}")
            logger.info(f"Start with: systemctl --user start {service_name}")
            logger.info(f"Status: systemctl --user status {service_name}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to reload systemd: {e.stderr.decode()}")


def uninstall_systemd_service(system_wide: bool = False) -> None:
    """
    Uninstall the awusb systemd service.

    Args:
        system_wide: If True, uninstall system service. If False, uninstall user service.

    Raises:
        RuntimeError: If uninstallation fails.
    """
    if system_wide:
        service_path = Path("/etc/systemd/system/awusb.service")
        service_name = "awusb.service"
    else:
        service_path = Path.home() / ".config" / "systemd" / "user" / "awusb.service"
        service_name = "awusb.service"

    if not service_path.exists():
        logger.warning(f"Service file not found: {service_path}")
        return

    # Stop and disable service first
    import subprocess

    try:
        if system_wide:
            subprocess.run(
                ["systemctl", "stop", service_name],
                check=False,
                capture_output=True,
            )
            subprocess.run(
                ["systemctl", "disable", service_name],
                check=False,
                capture_output=True,
            )
        else:
            subprocess.run(
                ["systemctl", "--user", "stop", service_name],
                check=False,
                capture_output=True,
            )
            subprocess.run(
                ["systemctl", "--user", "disable", service_name],
                check=False,
                capture_output=True,
            )
    except Exception as e:
        logger.warning(f"Error stopping/disabling service: {e}")

    # Remove service file
    try:
        service_path.unlink()
        logger.info(f"Removed service file: {service_path}")
    except PermissionError:
        if system_wide:
            raise RuntimeError("Permission denied. Run with sudo for system service.")
        raise

    # Reload systemd
    try:
        if system_wide:
            subprocess.run(
                ["systemctl", "daemon-reload"], check=True, capture_output=True
            )
        else:
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=True,
                capture_output=True,
            )
        logger.info("Service uninstalled successfully!")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to reload systemd: {e.stderr.decode()}")
