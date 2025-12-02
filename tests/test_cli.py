import subprocess
import sys

from awusb_client import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "awusb_client", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
