import socket

from pydantic import TypeAdapter

from .models import (
    AttachRequest,
    AttachResponse,
    ErrorResponse,
    ListRequest,
    ListResponse,
)
from .usbdevice import UsbDevice
from .utility import run_command


def send_request(request, server_host="localhost", server_port=5000):
    """
    Send a request to the server and return the response.

    Args:
        request: The request object to send
        server_host: Server hostname or IP address
        server_port: Server port number

    Returns:
        The response object from the server

    Raises:
        RuntimeError: If the server returns an error response
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((server_host, server_port))
        sock.sendall(request.model_dump_json().encode("utf-8"))

        response = sock.recv(4096).decode("utf-8")
        # Parse response using TypeAdapter to handle union types
        response_adapter = TypeAdapter(ListResponse | AttachResponse | ErrorResponse)
        decoded = response_adapter.validate_json(response)

        if isinstance(decoded, ErrorResponse):
            raise RuntimeError(f"Server error: {decoded.message}")

        return decoded


def list_devices(server_host="localhost", server_port=5000) -> list[UsbDevice]:
    """
    Request list of available USB devices from the server.

    Args:
        server_host: Server hostname or IP address
        server_port: Server port number

    Returns:
        List of UsbDevice instances
    """
    request = ListRequest()
    response = send_request(request, server_host, server_port)
    return response.data


def attach_detach_device(
    args: AttachRequest, server_host="localhost", server_port=5000, detach: bool = False
) -> UsbDevice:
    """
    Request to attach or detach a USB device from the server.

    Args:
        id: ID of the device to attach
        server_host: Server hostname or IP address
        server_port: Server port number

    Returns:
        The device that was attached, or detached
    """
    response = send_request(args, server_host, server_port)

    if not detach:
        run_command(
            [
                "sudo",
                "usbip",
                "attach",
                "-r",
                server_host,
                "-b",
                response.data.bus_id,
            ]
        )

    return response.data
