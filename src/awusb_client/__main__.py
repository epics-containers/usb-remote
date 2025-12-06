"""Interface for ``python -m awusb_client``."""

from collections.abc import Sequence

import typer

from . import __version__
from .client import attach_device, list_devices
from .models import AttachRequest
from .server import CommandServer
from .usbdevice import get_devices

__all__ = ["main"]

app = typer.Typer()


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
def server() -> None:
    """Start the USB sharing server."""
    server = CommandServer()
    server.start()


@app.command()
def list(
    local: bool = typer.Option(
        False,
        "--local",
        "-l",
        help="List local USB devices instead of querying the server",
    ),
) -> None:
    """List the available USB devices from the server."""
    if local:
        devices = get_devices()
    else:
        devices = list_devices()

    for device in devices:
        print(device)


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
    """Attach a USB device from the server."""
    args = AttachRequest(
        id=id,
        bus=bus,
        serial=serial,
        desc=desc,
    )
    result = attach_device(
        args=args,
        server_host=host if host else "localhost",
        server_port=5000,
    )

    if result:
        typer.echo("OK")


def main(args: Sequence[str] | None = None) -> None:
    """Argument parser for the CLI."""
    app()


if __name__ == "__main__":
    main()
