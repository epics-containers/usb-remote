"""Systemd service installation utilities."""

import getpass
import logging
import shutil
import sys
from pathlib import Path

from usb_remote.utility import run_command

logger = logging.getLogger(__name__)

SYSTEMD_SERVER_SERVICE_TEMPLATE = """[Unit]
Description=USB-Remote - USB Device Sharing Server
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={working_dir}
ExecStart={executable} -m usb_remote server
Restart=on-failure
RestartSec=5s

# Security hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
"""

SYSTEMD_CLIENT_SERVICE_TEMPLATE = """[Unit]
Description=USB-Remote - USB Device Sharing Client
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={working_dir}
ExecStart={executable} -m usb_remote client-service
Restart=on-failure
RestartSec=5s
RuntimeDirectory=usb-remote-client
RuntimeDirectoryMode=0755
# TODO : Change to an appropriate group if we need access from non-root users
RuntimeDirectoryGroup=root
ConfigurationDirectory=usb-remote-client
ConfigurationDirectoryMode=0755

# Security hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
"""


def get_systemd_service_content(
    user: str | None = None, service_type: str = "server"
) -> str:
    """
    Generate systemd service file content.

    Args:
        user: Username to run the service as. If None, uses current user.
        service_type: Type of service to install ("server" or "client").

    Returns:
        String content of the systemd service file.
    """
    if user is None:
        user = getpass.getuser()

    # Get the Python executable path
    executable = sys.executable

    # Use home directory as working directory
    working_dir = str(Path.home())

    template = (
        SYSTEMD_CLIENT_SERVICE_TEMPLATE
        if service_type == "client"
        else SYSTEMD_SERVER_SERVICE_TEMPLATE
    )

    return template.format(user=user, working_dir=working_dir, executable=executable)


def _get_service_paths(
    system_wide: bool, service_type: str = "server"
) -> tuple[Path, str]:
    """Get service directory and name based on installation type."""
    service_name = (
        f"usb-remote-{service_type}.service"
        if service_type == "client"
        else "usb-remote.service"
    )
    if system_wide:
        service_dir = Path("/etc/systemd/system")
    else:
        service_dir = Path.home() / ".config" / "systemd" / "user"
    return service_dir, service_name


def _run_systemctl(args: list[str], system_wide: bool, check: bool = True) -> None:
    """Run systemctl command with appropriate flags."""
    cmd = ["systemctl"]
    if not system_wide:
        cmd.append("--user")
    cmd.extend(args)
    run_command(cmd, check=check)


def install_systemd_service(
    user: str | None = None,
    system_wide: bool = True,
    service_type: str = "server",
) -> None:
    """
    Install the usb-remote service as a systemd service.

    Args:
        user: Username to run the service as. If None, uses current user.
        system_wide: If True, install as system service (requires root).
                    If False, install as user service. Defaults to True.
        service_type: Type of service to install ("server" or "client").
                     Defaults to "server".

    Raises:
        RuntimeError: If installation fails.
    """
    # Check if systemd is available
    if not shutil.which("systemctl"):
        raise RuntimeError("systemd not found. This command requires systemd.")

    service_content = get_systemd_service_content(user, service_type)
    service_dir, service_name = _get_service_paths(system_wide, service_type)
    service_path = service_dir / service_name

    # Create directory if it doesn't exist
    try:
        service_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        if system_wide:
            raise RuntimeError(
                "Permission denied. Run with sudo for system-wide installation."
            ) from e
        raise

    # Write service file
    try:
        service_path.write_text(service_content)
        logger.info(f"Service file written to {service_path}")
    except PermissionError as e:
        if system_wide:
            raise RuntimeError(
                "Permission denied. Run with sudo for system-wide installation."
            ) from e
        raise

    # Reload systemd
    try:
        _run_systemctl(["daemon-reload"], system_wide)
        scope = "System" if system_wide else "User"
        sudo = "sudo " if system_wide else ""
        user_flag = "" if system_wide else "--user "

        logger.info(f"{scope} service installed successfully!")
        logger.info(f"Enable with: {sudo}systemctl {user_flag}enable {service_name}")
        logger.info(f"Start with: {sudo}systemctl {user_flag}start {service_name}")
        logger.info(f"Status: {sudo}systemctl {user_flag}status {service_name}")
    except RuntimeError as e:
        raise RuntimeError(f"Failed to reload systemd: {e}") from e


def uninstall_systemd_service(
    system_wide: bool = True, service_type: str = "server"
) -> None:
    """
    Uninstall the usb-remote systemd service.

    Args:
        system_wide: True for system service. False for user service.
                    Defaults to True.
        service_type: Type of service to uninstall ("server" or "client").
                     Defaults to "server".

    Raises:
        RuntimeError: If uninstallation fails.
    """
    service_dir, service_name = _get_service_paths(system_wide, service_type)
    service_path = service_dir / service_name

    if not service_path.exists():
        logger.warning(f"Service file not found: {service_path}")
        return

    # Stop and disable service first (don't fail if already stopped)
    try:
        _run_systemctl(["stop", service_name], system_wide, check=False)
        _run_systemctl(["disable", service_name], system_wide, check=False)
    except Exception as e:
        logger.warning(f"Error stopping/disabling service: {e}")

    # Remove service file
    try:
        service_path.unlink()
        logger.info(f"Removed service file: {service_path}")
    except PermissionError as e:
        if system_wide:
            raise RuntimeError(
                "Permission denied. Run with sudo for system service."
            ) from e
        raise

    # Reload systemd
    try:
        _run_systemctl(["daemon-reload"], system_wide)
        logger.info("Service uninstalled successfully!")
    except RuntimeError as e:
        raise RuntimeError(f"Failed to reload systemd: {e}") from e
