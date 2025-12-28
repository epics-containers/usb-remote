import logging
import socket

from pydantic import TypeAdapter

from .api import (
    PORT,
    DeviceRequest,
    DeviceResponse,
    ErrorResponse,
    ListRequest,
    ListResponse,
    attach_command,
    detach_command,
    find_command,
)
from .config import get_timeout
from .port import Port
from .usbdevice import DeviceNotFoundError, MultipleDevicesError, UsbDevice
from .utility import run_command

logger = logging.getLogger(__name__)

# Default connection timeout in seconds
DEFAULT_TIMEOUT = 2.0


def send_request(
    request: ListRequest | DeviceRequest,
    server_host: str = "localhost",
    server_port: int = PORT,
    timeout: float | None = None,
) -> ListResponse | DeviceResponse:
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
            logger.debug(f"Received response from server: {response}")
            # Parse response using TypeAdapter to handle union types
            response_adapter = TypeAdapter(
                ListResponse | DeviceResponse | ErrorResponse
            )
            decoded = response_adapter.validate_json(response)

            if isinstance(decoded, ErrorResponse):
                match decoded.status:
                    case "not_found":
                        logger.debug(f"Device not found: {decoded.message}")
                        raise DeviceNotFoundError(f"{decoded.message}")
                    case "multiple_matches":
                        logger.debug(f"Multiple matches: {decoded.message}")
                        raise MultipleDevicesError(f"{decoded.message}")
                    case "error":
                        logger.debug(f"Server returned error: {decoded.message}")
                        raise RuntimeError(f"Server error: {decoded.message}")

            logger.debug(f"Request successful: {request.command}")
            return decoded

    except TimeoutError as e:
        msg = f"Connection to {server_host}:{server_port} timed out after {timeout}s"
        logger.warning(msg)
        raise TimeoutError(msg) from e


def list_devices(
    server_hosts: list[str],
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
            response = send_request(request, server, timeout=timeout)
            assert isinstance(response, ListResponse)
            results[server] = response.data
            logger.debug(f"Server {server}: {len(response.data)} devices")
        except DeviceNotFoundError:
            pass  # expect not to find the device on all servers
        except Exception as e:
            logger.warning(f"Failed to query server {server}: {e}")
            results[server] = []

    return results


def detach_local_device(bus_id: str, server_host: str) -> None:
    """
    Find a local usbip port by remote bus ID and server, then detach it.

    Args:
        bus_id: The remote bus ID of the device to detach
        server_host: The server hostname or IP address
    """
    try:
        port = Port.get_port_by_remote_busid(bus_id, server_host)
        if port is not None:
            logger.info(f"Found local port {port.port} for device {bus_id}, detaching")
            run_command(["sudo", "usbip", "detach", "-p", port.port])
    except Exception as e:
        print(e)
        logger.warning(f"Failed to detach device {bus_id} locally: {e}")


def attach_device(bus_id: str, server_host: str) -> None:
    """
    Attach a USB device by bus ID from a specific server.

    Args:
        bus_id: The bus ID of the device to attach
        server_host: Server hostname or IP address
        timeout: Connection timeout in seconds. If None, uses configured timeout.
    """

    # occasionally if a remote server has been restarted, the local port
    # may still be attached even though the remote device is gone -
    # try to detach it first to be safe
    detach_local_device(bus_id, server_host)

    logger.debug(f"Asking remote {server_host} to bind {bus_id} to usbip")
    request = DeviceRequest(
        command=attach_command,
        bus=bus_id,
    )
    send_request(request, server_host)

    logger.info(f"Attaching device {bus_id} from {server_host} to local system")
    run_command(
        [
            "sudo",
            "usbip",
            "attach",
            "-r",
            server_host,
            "-b",
            bus_id,
        ]
    )


def detach_device(bus_id: str, server_host: str) -> None:
    """
    Detach a USB device by bus ID from a specific server.

    Args:
        bus_id: The bus ID of the device to detach
        server_host: Server hostname or IP address
        timeout: Connection timeout in seconds. If None, uses configured timeout.
    """
    detach_local_device(bus_id, server_host)

    logger.debug(f"Asking remote {server_host} to unbind {bus_id} from usbip")
    request = DeviceRequest(
        command=detach_command,
        bus=bus_id,
    )
    send_request(request, server_host)

    logger.info(f"Device detached: {server_host}:{bus_id}")


def find_device(
    server_hosts: list[str],
    id: str | None = None,
    bus: str | None = None,
    desc: str | None = None,
    serial: str | None = None,
    first: bool = False,
) -> tuple[UsbDevice, str]:
    """
    Request to find a USB device from server(s). Will only return
    a single device, or raise an error if multiple matches found.

    If args.first is set, will return the first match found across all
    servers.

    Args:
        args: AttachRequest with device search criteria
        server_hosts: list of server hostnames/IPs
        timeout: Connection timeout in seconds. If None, uses configured timeout.

    Returns:
        The UsbDevice and the host where device was found

    Raises:
        RuntimeError: If device not found or multiple matches found (list mode only)
    """

    logger.info(
        f"Scanning {len(server_hosts)} for device matching {id}, {bus},"
        f" {desc}, {serial}, {first}"
    )

    request = DeviceRequest(
        command=find_command,
        id=id,
        bus=bus,
        desc=desc,
        first=first,
        serial=serial,
    )

    matches = []

    for server in server_hosts:
        try:
            logger.debug(f"Trying server {server}")
            response = send_request(request, server)
            assert isinstance(response, DeviceResponse)
            matches.append((response.data, server))
            logger.debug(f"Match found on {server}: {response.data.description}")
        except DeviceNotFoundError as e:
            # It is OK to not find the device on one of the servers
            logger.debug(f"Server {server}:\n{e}")
            continue
        except MultipleDevicesError as e:
            # Multiple matches on this server
            raise RuntimeError(f"Server {server}:\n{e}") from e
        except Exception as e:
            # Server returned a generic error - continue to next server
            logger.error(f"Server {server}:\n {e}")
            continue

    if len(matches) == 0:
        msg = f"No matching device found across {len(server_hosts)} servers"
        logger.debug(msg, exc_info=True)
        raise DeviceNotFoundError(msg)

    if len(matches) > 1 and not request.first:
        device_list = "\n".join(f"  {dev} (on {srv})" for dev, srv in matches)
        msg = (
            f"Multiple devices matched across servers:\n{device_list}\n\n"
            "Use --first to attach to the first match."
        )
        logger.debug(msg, exc_info=True)
        raise MultipleDevicesError(msg)

    device, server = matches[0]

    return device, server
