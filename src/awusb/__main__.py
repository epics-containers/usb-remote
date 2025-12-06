"""Interface for ``python -m awusb``."""

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import typer

from . import __version__
from .client import attach_detach_device, list_devices
from .config import get_servers
from .models import AttachRequest
from .server import CommandServer
from .service import install_systemd_service, uninstall_systemd_service
from .usbdevice import UsbDevice, get_devices

__all__ = ["main"]

app = typer.Typer()
logger = logging.getLogger(__name__)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"awusb {__version__}")
        raise typer.Exit()


@app.callback()
def common_options(
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Common options for all commands."""
    pass


@app.command()
def server(
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug logging"),
) -> None:
    """Start the USB sharing server."""
    # Configure logging
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info(f"Starting server with log level: {logging.getLevelName(log_level)}")
    server = CommandServer()
    server.start()


@app.command(name="list")
def list_command(
    local: bool = typer.Option(
        False,
        "--local",
        "-l",
        help="List local USB devices instead of querying the server",
    ),
    host: str | None = typer.Option(
        None, "--host", "-H", help="Server hostname or IP address"
    ),
    config: Path | None = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """List the available USB devices from the server(s)."""
    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    if local:
        logger.debug("Listing local USB devices")
        devices = get_devices()
        for device in devices:
            print(device)
    elif host:
        # Single server specified
        logger.debug(f"Listing devices from {host}")
        devices = cast(
            list[UsbDevice], list_devices(server_hosts=host, server_port=5055)
        )
        for device in devices:
            print(device)
    else:
        # Query all servers from config
        servers = get_servers(config)
        if not servers:
            logger.warning("No servers configured, defaulting to localhost")
            servers = ["localhost"]

        results = cast(
            dict[str, list[UsbDevice]],
            list_devices(server_hosts=servers, server_port=5055),
        )
        for server, devices in results.items():
            print(f"\n=== {server} ===")
            if devices:
                for device in devices:
                    print(device)
            else:
                print("No devices or server unavailable")


def attach_detach(detach: bool = False, **kwargs) -> tuple[UsbDevice, str | None]:
    """Attach or detach a USB device from the server.

    Returns:
        Tuple of (device, server) where server is None if --host was specified
    """
    args = AttachRequest(detach=detach, **kwargs)
    host = kwargs.get("host")
    config = kwargs.get("config")

    if host:
        # Single server specified
        result = attach_detach_device(
            args=args,
            server_hosts=host,
            server_port=5055,
            detach=detach,
        )
        device = cast(UsbDevice, result)
        return device, None
    else:
        # Scan all servers from config
        servers = get_servers(config)
        if not servers:
            logger.warning("No servers configured, defaulting to localhost")
            servers = ["localhost"]

        result = attach_detach_device(
            args=args,
            server_hosts=servers,
            server_port=5055,
            detach=detach,
        )
        device, server = cast(tuple[UsbDevice, str], result)
        return device, server


@app.command()
def attach(
    id: str | None = typer.Option(None, "--id", "-d", help="Device ID e.g. 0bda:5400"),
    serial: str | None = typer.Option(
        None, "--serial", "-s", help="Device serial number"
    ),
    desc: str | None = typer.Option(
        None, "--desc", help="Device description substring"
    ),
    host: str | None = typer.Option(
        None, "--host", "-H", help="Server hostname or IP address"
    ),
    bus: str | None = typer.Option(
        None, "--bus", "-b", help="Device bus ID e.g. 1-2.3.4"
    ),
    first: bool = typer.Option(
        False, "--first", "-f", help="Attach the first match if multiple found"
    ),
    config: Path | None = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """Attach a USB device from the server."""
    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    result, server = attach_detach(
        False,
        id=id,
        bus=bus,
        desc=desc,
        first=first,
        serial=serial,
        host=host,
        config=config,
    )
    if server:
        typer.echo(f"Attached to device on {server}:\n{result}")
    else:
        typer.echo(f"Attached to:\n{result}")


@app.command()
def detach(
    id: str | None = typer.Option(None, "--id", "-d", help="Device ID e.g. 0bda:5400"),
    serial: str | None = typer.Option(
        None, "--serial", "-s", help="Device serial number"
    ),
    desc: str | None = typer.Option(
        None, "--desc", help="Device description substring"
    ),
    host: str | None = typer.Option(
        None, "--host", "-H", help="Server hostname or IP address"
    ),
    bus: str | None = typer.Option(
        None, "--bus", "-b", help="Device bus ID e.g. 1-2.3.4"
    ),
    first: bool = typer.Option(
        False, "--first", "-f", help="Attach the first match if multiple found"
    ),
    config: Path | None = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """Detach a USB device from the server."""
    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    result, server = attach_detach(
        True,
        id=id,
        bus=bus,
        desc=desc,
        first=first,
        serial=serial,
        host=host,
        config=config,
    )
    if server:
        typer.echo(f"Detached from device on {server}:\n{result}")
    else:
        typer.echo(f"Detached from:\n{result}")


@app.command()
def install_service(
    system: bool = typer.Option(
        False,
        "--system",
        help="Install as system service (requires sudo/root)",
    ),
    user: str | None = typer.Option(
        None,
        "--user",
        "-u",
        help="User to run the service as (default: current user)",
    ),
) -> None:
    """Install awusb server as a systemd service."""
    try:
        install_systemd_service(user=user, system_wide=system)
    except RuntimeError as e:
        typer.echo(f"Installation failed: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def uninstall_service(
    system: bool = typer.Option(
        False,
        "--system",
        help="Uninstall system service (requires sudo/root)",
    ),
) -> None:
    """Uninstall awusb server systemd service."""
    try:
        uninstall_systemd_service(system_wide=system)
    except RuntimeError as e:
        typer.echo(f"Uninstallation failed: {e}", err=True)
        raise typer.Exit(1)


def main(args: Sequence[str] | None = None) -> None:
    """Argument parser for the CLI."""
    try:
        app()
    except RuntimeError as e:
        typer.echo(f"Error: {e}", err=True)


if __name__ == "__main__":
    main()
