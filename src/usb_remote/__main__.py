"""Interface for ``python -m usb_remote``."""

import logging
from collections.abc import Sequence
from enum import Enum
from typing import Annotated

import typer

from usb_remote.port import Port

from . import __version__
from .client import attach_device, detach_device, find_device, list_devices
from .client_service import ClientService
from .config import (
    DEFAULT_CONFIG_PATH,
    discover_config_path,
    get_config,
    get_servers,
    save_servers,
)
from .server import CommandServer
from .service import install_systemd_service, uninstall_systemd_service
from .usbdevice import get_devices
from .utility import get_host_list

__all__ = ["main"]

app = typer.Typer()
config_app = typer.Typer()
app.add_typer(config_app, name="config", help="Manage configuration")
logger = logging.getLogger(__name__)


class ServiceType(str, Enum):
    """Service type for systemd installation."""

    SERVER = "server"
    CLIENT = "client"


def version_callback(value: bool) -> None:
    """Output version and exit."""
    if value:
        typer.echo(f"usb-remote {__version__}")
        raise typer.Exit()


def setup_logging(log_level: int) -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )


@app.callback()
def common_options(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """Common options for all commands."""
    # Configure debug logging, all commands
    if debug:
        setup_logging(logging.DEBUG)

    # Store debug flag in context for commands that need it
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug


@app.command()
def ports() -> None:
    """List the local usbip ports in use."""
    ports = Port.list_ports()
    if not ports:
        typer.echo("No local usbip ports in use.")
        return

    for port in ports:
        typer.echo(port)


@app.command()
def server(
    ctx: typer.Context,
) -> None:
    """Start the USB sharing server."""
    debug = ctx.obj.get("debug", False)
    log_level = logging.DEBUG if debug else logging.INFO

    # Set log level for non-debug mode (debug mode already configured in callback)
    if not debug:
        setup_logging(logging.INFO)

    logger.info(
        f"Starting server {__version__} with log level: "
        f"{logging.getLevelName(log_level)}"
    )
    server = CommandServer()
    server.start()


@app.command(name="client-service")
def client_service_command(
    ctx: typer.Context,
) -> None:
    """Start the USB client service that accepts socket commands."""
    debug = ctx.obj.get("debug", False)
    log_level = logging.DEBUG if debug else logging.INFO

    # Set log level for non-debug mode (debug mode already configured in callback)
    if not debug:
        setup_logging(logging.INFO)

    logger.info(
        f"Starting client service {__version__} with log level: "
        f"{logging.getLevelName(log_level)}"
    )
    service = ClientService()
    service.start()


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
) -> None:
    """List the available USB devices from configured server(s)."""
    if local:
        logger.debug("Listing local USB devices")
        devices = get_devices()
        for device in devices:
            typer.echo(device)
    else:
        if host:
            servers = [host]
        else:
            servers = get_servers()
        if not servers:
            logger.warning("No servers configured, defaulting to localhost")
            servers = ["localhost"]

        logger.debug(f"Listing remote USB devices on hosts: {servers}")

        results = list_devices(server_hosts=servers)

        for server, devices in results.items():
            typer.echo(f"\n=== {server} ===")
            if devices:
                for device in devices:
                    typer.echo(device)
            else:
                typer.echo("No devices")


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
) -> None:
    """Attach a USB device from a server."""

    device, server = find_device(
        server_hosts=get_host_list(host),
        id=id,
        bus=bus,
        desc=desc,
        first=first,
        serial=serial,
    )
    attach_device(device.bus_id, server)
    # discover the local port for the attached device
    local_port = Port.get_port_by_remote_busid(device.bus_id, server, retries=20)

    typer.echo(f"Attached to device on {server}:\n{device}")
    if local_port:
        typer.echo(f"\nLocal port: {local_port}")
    else:
        typer.echo("Local device files not found (may still be initializing)")


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
) -> None:
    """Detach a USB device from a server."""

    device, server = find_device(
        server_hosts=get_host_list(host),
        id=id,
        bus=bus,
        desc=desc,
        first=first,
        serial=serial,
    )
    detach_device(device.bus_id, server)

    typer.echo(f"Detached from device on {server}:\n{device}")


@app.command()
def find(
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
) -> None:
    """Find a USB device on a server."""

    device, server = find_device(
        server_hosts=get_host_list(host),
        id=id,
        bus=bus,
        desc=desc,
        first=first,
        serial=serial,
    )

    typer.echo(f"Found device on {server}:\n{device}")


@app.command()
def install_service(
    service_type: Annotated[
        ServiceType,
        typer.Argument(help="Service type to install: 'server' or 'client'"),
    ] = ServiceType.SERVER,
    user_service: bool = typer.Option(
        False,
        "--user-service",
        help="Install as user service instead of system service",
    ),
    user: str | None = typer.Option(
        None,
        "--user",
        "-u",
        help="User to run the service as (default: current user)",
    ),
) -> None:
    """Install usb-remote service as a systemd service (defaults to system service)."""
    try:
        install_systemd_service(
            user=user, system_wide=not user_service, service_type=service_type.value
        )
    except RuntimeError as e:
        typer.echo(f"Installation failed: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def uninstall_service(
    service_type: Annotated[
        ServiceType,
        typer.Argument(help="Service type to uninstall: 'server' or 'client'"),
    ] = ServiceType.SERVER,
    user_service: bool = typer.Option(
        False,
        "--user-service",
        help="Uninstall user service instead of system service",
    ),
) -> None:
    """Uninstall usb-remote systemd service (defaults to system service)."""
    try:
        uninstall_systemd_service(
            system_wide=not user_service, service_type=service_type.value
        )
    except RuntimeError as e:
        typer.echo(f"Uninstallation failed: {e}", err=True)
        raise typer.Exit(1) from e


@config_app.command(name="show")
def config_show() -> None:
    """Show current configuration."""
    config_path = discover_config_path()

    if config_path is None:
        typer.echo("No configuration file found.")
        typer.echo(f"Default location: {DEFAULT_CONFIG_PATH}")
        typer.echo("\nDefault configuration:")
    else:
        typer.echo(f"Configuration file: {config_path}")
        typer.echo()

    config = get_config()

    typer.echo(f"Servers ({len(config.servers)}):")
    if config.servers:
        for server in config.servers:
            typer.echo(f"  - {server}")
    else:
        typer.echo("  (none)")

    typer.echo(f"\nTimeout: {config.timeout}s")


@config_app.command(name="add-server")
def config_add_server(
    server: str = typer.Argument(..., help="Server hostname or IP address"),
) -> None:
    """Add a server to the configuration."""
    config = get_config()

    if server in config.servers:
        typer.echo(f"Server '{server}' is already in the configuration.", err=True)
        raise typer.Exit(1)

    config.servers.append(server)
    save_servers(config.servers)

    config_path = discover_config_path() or DEFAULT_CONFIG_PATH
    typer.echo(f"Added server '{server}' to {config_path}")


@config_app.command(name="rm-server")
def config_remove_server(
    server: str = typer.Argument(..., help="Server hostname or IP address"),
) -> None:
    """Remove a server from the configuration."""
    config_path = discover_config_path()

    if config_path is None:
        typer.echo("No configuration file found.", err=True)
        raise typer.Exit(1)

    config = get_config()

    if server not in config.servers:
        typer.echo(f"Server '{server}' is not in the configuration.", err=True)
        raise typer.Exit(1)

    config.servers.remove(server)
    save_servers(config.servers)
    typer.echo(f"Removed server '{server}' from {config_path}")


@config_app.command(name="set-timeout")
def config_set_timeout(
    timeout: float = typer.Argument(..., help="Connection timeout in seconds"),
) -> None:
    """Set the connection timeout."""
    if timeout <= 0:
        typer.echo("Timeout must be greater than 0.", err=True)
        raise typer.Exit(1)

    config = get_config()
    config.timeout = timeout
    config.to_file()

    config_path = discover_config_path() or DEFAULT_CONFIG_PATH
    typer.echo(f"Set timeout to {timeout}s in {config_path}")


def main(args: Sequence[str] | None = None) -> None:
    """Argument parser for the CLI."""
    try:
        app()
    except Exception as e:
        logger.debug("Exception caught in main()", exc_info=True)
        typer.echo(f"ERROR: {e}", err=True)


if __name__ == "__main__":
    main()
