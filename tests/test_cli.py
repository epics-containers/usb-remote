import subprocess
import sys

from awusb import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "awusb", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == f"awusb {__version__}"
