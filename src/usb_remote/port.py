"""
Module for working with local usbip ports.
"""

import re
from dataclasses import dataclass

from usb_remote.utility import run_command

# regex pattern for matching 'usbip port' output https://regex101.com/r/seWBvX/1
re_ports = re.compile(
    r"[pP]ort *(?P<port>\d\d)[\s\S]*?\n *(?P<description>.*)\n[\s\S]*?usbip:\/\/(?P<server>[^:]*):\d*\/(?P<remote_busid>[1-9-.]*)"  # noqa: E501
)


@dataclass
class Port:
    """
    A class for discovering which local usbip ports are in use and detaching from
    those that match the user search criteria.
    """

    port: str  # the local port number
    server: str  # the server ip address
    description: str  # the device description (vendor and product)
    remote_busid: str  # the remote busid of the device

    def __post_init__(self):
        # everything is strings from the regex, convert port to int
        self.port_number = int(self.port)

    def detach(self) -> None:
        """Detach this port from the local system."""

        # don't raise an exception if detach fails because the port may already
        # be detached
        run_command(
            ["sudo", "usbip", "detach", "-p", str(self.port_number)], check=False
        )

    def __repr__(self) -> str:
        return (
            f"- Port {self.port_number}:\n  "
            f"{self.description}\n  "
            f"busid: {self.remote_busid} from {self.server}"
        )

    @staticmethod
    def list_ports() -> list["Port"]:
        """Lists the local usbip ports in use.

        Returns:
            A list of Port objects, each representing a port in use.
        """

        output = run_command(["sudo", "usbip", "port"]).stdout
        ports: list[Port] = []
        for match in re_ports.finditer(output):
            port_info = match.groupdict()
            ports.append(Port(**port_info))
        return ports

    @classmethod
    def get_port_by_remote_busid(cls, remote_busid: str, server: str) -> "Port | None":
        """Get a Port object by its remote busid.

        Args:
            server: The server ip address to search.
            remote_busid: The remote busid to search for.

        Returns:
            The Port of the local mount of the remote device if found, otherwise None.
            There can be only one match as port ids are unique per server.
        """
        ports = cls.list_ports()
        for port in ports:
            if port.remote_busid == remote_busid and port.server == server:
                return port
        return None
