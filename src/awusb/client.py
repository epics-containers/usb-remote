import logging
import socket

from pydantic import TypeAdapter

from .config import get_timeout
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

# Default connection timeout in seconds
DEFAULT_TIMEOUT = 5.0


def send_request(
    request,
    server_host="localhost",
    server_port=5055,
    raise_on_error=True,
    timeout: float | None = DEFAULT_TIMEOUT,
):
    """
    Send a request to the server and return the response.

    Args:
        request: The request object to send
        server_host: Server hostname or IP address
        server_port: Server port number
        raise_on_error: If True, log errors and raise RuntimeError on error response.
                       If False, just raise RuntimeError without logging.
        timeout: Connection timeout in seconds

    Returns:
        The response object from the server

    Raises:
        RuntimeError: If the server returns an error response
        TimeoutError: If connection or receive times out
        OSError: If connection fails
    """
    logger.debug(f"Connecting to server at {server_host}:{server_port}")

    if timeout is None:
        timeout = get_timeout()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect((server_host, server_port))
            logger.debug(f"Sending request: {request.command}")
            sock.sendall(request.model_dump_json().encode("utf-8"))

            response = sock.recv(4096).decode("utf-8")
            logger.debug("Received response from server")
            # Parse response using TypeAdapter to handle union types
            response_adapter = TypeAdapter(
                ListResponse | AttachResponse | ErrorResponse
            )
            decoded = response_adapter.validate_json(response)

            if isinstance(decoded, ErrorResponse):
                if raise_on_error:
                    logger.error(f"Server returned error: {decoded.message}")
                raise RuntimeError(f"Server error: {decoded.message}")

            logger.debug(f"Request successful: {request.command}")
            return decoded
    except TimeoutError as e:
        msg = f"Connection to {server_host}:{server_port} timed out after {timeout}s"
        logger.warning(msg)
        raise TimeoutError(msg) from e


def list_devices(
    server_hosts: list[str],
    server_port=5055,
    timeout: float | None = None,
) -> dict[str, list[UsbDevice]]:
    """
    Request list of available USB devices from server(s).

    Args:
        server_hosts: Single server hostname/IP or list of server hostnames/IPs
        server_port: Server port number
        timeout: Connection timeout in seconds. If None, uses configured timeout.

    Returns:
        If server_hosts is a string: List of UsbDevice instances
        If server_hosts is a list: Dictionary mapping server name to
            list of UsbDevice instances
    """

    logger.info(f"Querying {len(server_hosts)} servers for device lists")
    results = {}

    for server in server_hosts:
        try:
            request = ListRequest()
            response = send_request(request, server, server_port, timeout=timeout)
            results[server] = response.data
            logger.debug(f"Server {server}: {len(response.data)} devices")
        except Exception as e:
            logger.warning(f"Failed to query server {server}: {e}")
            results[server] = []

    return results


def attach_detach_device(
    args: AttachRequest,
    server_hosts: list[str],
    server_port=5055,
    detach: bool = False,
    timeout: float | None = None,
) -> tuple[UsbDevice, str]:
    """
    Request to attach or detach a USB device from server(s).

    Args:
        args: AttachRequest with device search criteria
        server_hosts: list of server hostnames/IPs
        server_port: Server port number
        detach: Whether to detach instead of attach
        timeout: Connection timeout in seconds. If None, uses configured timeout.

    Returns:
        If server_hosts is a string: Tuple of (UsbDevice, None)
        If server_hosts is a list: Tuple of (UsbDevice, server_host)
            where device was found

    Raises:
        RuntimeError: If device not found or multiple matches found (list mode only)
    """
    action = "detach" if detach else "attach"

    logger.info(f"Scanning {len(server_hosts)} servers for device to {action}")
    matches = []

    for server in server_hosts:
        try:
            logger.debug(f"Trying server {server}")
            response = send_request(
                args, server, server_port, raise_on_error=False, timeout=timeout
            )
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
        device_list = "\n".join(f"  {dev} (on {srv})" for dev, srv in matches)
        msg = (
            f"Multiple devices matched across servers:\n{device_list}\n\n"
            "Use --first to attach the first match."
        )
        raise RuntimeError(msg)

    device, server = matches[0]

    if detach:
        logger.info(f"Device detached: {device.description}")
    else:
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

    logger.info(f"Device {action}ed on server {server}: {device.description}")
    return device, server
