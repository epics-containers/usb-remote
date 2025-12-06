import socket

from pydantic import TypeAdapter

from awusb.models import (
    AttachRequest,
    AttachResponse,
    ErrorResponse,
    ListRequest,
    ListResponse,
)
from awusb.usbdevice import UsbDevice


def send_request(sock, request):
    sock.sendall(request.model_dump_json().encode("utf-8"))

    response = sock.recv(4096).decode("utf-8")
    # Parse response using TypeAdapter to handle union types
    response_adapter = TypeAdapter(ListResponse | AttachResponse | ErrorResponse)
    decoded = response_adapter.validate_json(response)

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
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((server_host, server_port))

        request = ListRequest()
        response = send_request(sock, request)

        if isinstance(response, ErrorResponse):
            raise RuntimeError(f"Server error: {response.message}")

        return response.data


def attach_device(
    args: AttachRequest, server_host="localhost", server_port=5000
) -> bool:
    """
    Request to attach a USB device from the server.

    Args:
        id: ID of the device to attach
        server_host: Server hostname or IP address
        server_port: Server port number

    Returns:
        True if successful, False otherwise
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((server_host, server_port))

        print(f"Request: {args}")
        response = send_request(sock, args)

        if isinstance(response, ErrorResponse):
            raise RuntimeError(f"Server error: {response.message}")

        return response.status == "success"
