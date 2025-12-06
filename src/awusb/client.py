import logging
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

logger = logging.getLogger(__name__)


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
    logger.debug(f"Connecting to server at {server_host}:{server_port}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((server_host, server_port))
        logger.debug(f"Sending request: {request.command}")
        sock.sendall(request.model_dump_json().encode("utf-8"))

        response = sock.recv(4096).decode("utf-8")
        logger.debug("Received response from server")
        # Parse response using TypeAdapter to handle union types
        response_adapter = TypeAdapter(ListResponse | AttachResponse | ErrorResponse)
        decoded = response_adapter.validate_json(response)

        if isinstance(decoded, ErrorResponse):
            logger.error(f"Server returned error: {decoded.message}")
            raise RuntimeError(f"Server error: {decoded.message}")

        logger.debug(f"Request successful: {request.command}")
        return decoded


def list_devices(
    server_hosts: list[str] | str = "localhost", server_port=5000
) -> dict[str, list[UsbDevice]] | list[UsbDevice]:
    """
    Request list of available USB devices from server(s).

    Args:
        server_hosts: Single server hostname/IP or list of server hostnames/IPs
        server_port: Server port number

    Returns:
        If server_hosts is a string: List of UsbDevice instances
        If server_hosts is a list: Dictionary mapping server name to list of UsbDevice instances
    """
    # Handle single server (backward compatibility)
    if isinstance(server_hosts, str):
        logger.info(f"Requesting device list from {server_hosts}:{server_port}")
        request = ListRequest()
        response = send_request(request, server_hosts, server_port)
        logger.info(f"Retrieved {len(response.data)} devices")
        return response.data

    # Handle multiple servers
    logger.info(f"Querying {len(server_hosts)} servers for device lists")
    results = {}

    for server in server_hosts:
        try:
            request = ListRequest()
            response = send_request(request, server, server_port)
            results[server] = response.data
            logger.debug(f"Server {server}: {len(response.data)} devices")
        except Exception as e:
            logger.warning(f"Failed to query server {server}: {e}")
            results[server] = []

    return results


def attach_detach_device(
    args: AttachRequest,
    server_hosts: list[str] | str = "localhost",
    server_port=5000,
    detach: bool = False,
) -> UsbDevice | tuple[UsbDevice, str]:
    """
    Request to attach or detach a USB device from server(s).

    Args:
        args: AttachRequest with device search criteria
        server_hosts: Single server hostname/IP or list of server hostnames/IPs
        server_port: Server port number
        detach: Whether to detach instead of attach

    Returns:
        If server_hosts is a string: UsbDevice that was attached/detached
        If server_hosts is a list: Tuple of (UsbDevice, server_host) where device was found

    Raises:
        RuntimeError: If device not found or multiple matches found (list mode only)
    """
    action = "detach" if detach else "attach"

    # Handle single server (backward compatibility)
    if isinstance(server_hosts, str):
        logger.info(f"Requesting {action} from {server_hosts}:{server_port}")
        response = send_request(args, server_hosts, server_port)

        if not detach:
            logger.info(f"Attaching device {response.data.bus_id} to local system")
            run_command(
                [
                    "sudo",
                    "usbip",
                    "attach",
                    "-r",
                    server_hosts,
                    "-b",
                    response.data.bus_id,
                ]
            )
            logger.info(f"Device attached successfully: {response.data.description}")
        else:
            logger.info(f"Device detached: {response.data.description}")

        return response.data

    # Handle multiple servers
    logger.info(f"Scanning {len(server_hosts)} servers for device to {action}")
    matches = []

    for server in server_hosts:
        try:
            logger.debug(f"Trying server {server}")
            response = send_request(args, server, server_port)
            matches.append((response.data, server))
            logger.debug(f"Match found on {server}: {response.data.description}")
        except RuntimeError as e:
            # Server returned an error (no match or multiple matches on this server)
            logger.debug(f"Server {server}: {e}")
            continue
        except Exception as e:
            # Connection or other error
            logger.warning(f"Failed to query server {server}: {e}")
            continue

    if len(matches) == 0:
        msg = f"No matching device found across {len(server_hosts)} servers"
        logger.error(msg)
        raise RuntimeError(msg)

    if len(matches) > 1 and not args.first:
        server_list = ", ".join(f"{dev.description} on {srv}" for dev, srv in matches)
        msg = (
            f"Multiple devices matched across servers: {server_list}. "
            "Use --first to attach the first match."
        )
        logger.error(msg)
        raise RuntimeError(msg)

    device, server = matches[0]

    if not detach:
        logger.info(f"Attaching device {device.bus_id} from {server} to local system")
        run_command(
            [
                "sudo",
                "usbip",
                "attach",
                "-r",
                server,
                "-b",
                device.bus_id,
            ]
        )
        logger.info(f"Device attached: {device.description}")
    else:
        logger.info(f"Device detached: {device.description}")

    logger.info(f"Device {action}ed on server {server}: {device.description}")
    return device, server
