"""Interface for ``python -m awusb``."""

import logging
from collections.abc import Sequence
from typing import cast

import typer

from awusb.port import Port

from . import __version__
from .client import attach_detach_device, list_devices
from .config import (
    DEFAULT_CONFIG_PATH,
    discover_config_path,
    get_config,
    get_servers,
    save_servers,
)
from .models import AttachRequest
from .server import CommandServer
from .service import install_systemd_service, uninstall_systemd_service
from .usbdevice import UsbDevice, get_devices

__all__ = ["main"]

app = typer.Typer()
config_app = typer.Typer()
app.add_typer(config_app, name="config", help="Manage configuration")
logger = logging.getLogger(__name__)


def version_callback(value: bool) -> None:
    """Output version and exit."""
    if value:
        typer.echo(f"awusb {__version__}")
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
        typer.echo(
            f"Port {port.port_number}:\n  {port.description} "
            f"\n  ({port.id}) from {port.server} busid {port.remote_busid}"
        )


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

        results = list_devices(server_hosts=servers, server_port=5055)

        for server, devices in results.items():
            typer.echo(f"\n=== {server} ===")
            if devices:
                for device in devices:
                    typer.echo(device)
            else:
                typer.echo("No devices or server unavailable")


def attach_detach(detach: bool = False, **kwargs) -> tuple[UsbDevice, str | None]:
    """Attach or detach a USB device from a server.

    Returns:
        Tuple of (device, server) where server is None if --host was specified
    """
    args = AttachRequest(detach=detach, **kwargs)
    host = kwargs.get("host")

    if host:
        servers = [host]
    else:
        servers = get_servers()
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
) -> None:
    """Attach a USB device from a server."""
    result, server = attach_detach(
        False,
        id=id,
        bus=bus,
        desc=desc,
        first=first,
        serial=serial,
        host=host,
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
) -> None:
    """Detach a USB device from a server."""
    result, server = attach_detach(
        True,
        id=id,
        bus=bus,
        desc=desc,
        first=first,
        serial=serial,
        host=host,
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
        raise typer.Exit(1) from e


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
    except RuntimeError as e:
        typer.echo(f"Error: {e}", err=True)


if __name__ == "__main__":
    main()
