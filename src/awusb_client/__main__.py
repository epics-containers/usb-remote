"""Interface for ``python -m awusb_client``."""

from argparse import ArgumentParser
from collections.abc import Sequence

from . import __version__
from .usbdevice import get_devices

__all__ = ["main"]


def main(args: Sequence[str] | None = None) -> None:
    """Argument parser for the CLI."""
    parser = ArgumentParser()
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
    )
    parser.parse_args(args)

    get_devices_list = get_devices()
    print("Local shareable USB devices:")
    for device in get_devices_list:
        print(f"- {device}")


if __name__ == "__main__":
    main()
