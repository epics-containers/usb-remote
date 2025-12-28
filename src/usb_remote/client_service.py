"""Client service that accepts socket commands to attach/detach USB devices."""

import logging
import socket
import threading
from typing import Literal

from pydantic import TypeAdapter, ValidationError

from .client import attach_device, detach_device, find_device
from .client_api import (
    CLIENT_PORT,
    ClientDeviceRequest,
    ClientDeviceResponse,
    ClientErrorResponse,
    error_response,
    multiple_matches_response,
    not_found_response,
)
from .config import get_servers
from .port import Port
from .usbdevice import DeviceNotFoundError, MultipleDevicesError

logger = logging.getLogger(__name__)


class ClientService:
    """Service that runs a socket server to accept attach/detach commands."""

    def __init__(self, host: str = "127.0.0.1", port: int = CLIENT_PORT):
        """
        Initialize the client service.

        Args:
            host: Host to bind the socket server to (default: localhost only)
            port: Port to bind the socket server to
        """
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False

    def get_host_list(self, host: str | None) -> list[str]:
        """Get list of server hosts from argument or config."""
        if host:
            servers = [host]
        else:
            servers = get_servers()
        if not servers:
            logger.warning("No servers configured, defaulting to localhost")
            servers = ["localhost"]
        return servers

    def handle_attach(self, args: ClientDeviceRequest) -> tuple[str, str]:
        """
        Handle attach command.

        Args:
            args: ClientDeviceRequest with device search criteria

        Returns:
            Tuple of (server host, bus_id) where device was attached

        Raises:
            DeviceNotFoundError: If device not found
            MultipleDevicesError: If multiple devices match and first not set
        """
        server_hosts = self.get_host_list(args.host)

        logger.info(
            f"Searching for device to attach across {len(server_hosts)} servers"
        )
        device, server = find_device(
            server_hosts=server_hosts,
            id=args.id,
            bus=args.bus,
            desc=args.desc,
            first=args.first,
            serial=args.serial,
        )

        logger.info(f"Attaching device {device.bus_id} from {server}")
        attach_device(device.bus_id, server)

        return server, device.bus_id

    def handle_detach(self, args: ClientDeviceRequest) -> tuple[str, str]:
        """
        Handle detach command.

        Args:
            args: ClientDeviceRequest with device search criteria

        Returns:
            Tuple of (server host, bus_id) where device was detached

        Raises:
            DeviceNotFoundError: If device not found
            MultipleDevicesError: If multiple devices match and first not set
        """
        server_hosts = self.get_host_list(args.host)

        logger.info(
            f"Searching for device to detach across {len(server_hosts)} servers"
        )
        device, server = find_device(
            server_hosts=server_hosts,
            id=args.id,
            bus=args.bus,
            desc=args.desc,
            first=args.first,
            serial=args.serial,
        )

        logger.info(f"Detaching device {device.bus_id} from {server}")
        detach_device(device.bus_id, server)

        return server, device.bus_id

    def handle_device_command(self, args: ClientDeviceRequest) -> ClientDeviceResponse:
        """
        Handle attach or detach command.

        Args:
            args: ClientDeviceRequest with command and device criteria

        Returns:
            ClientDeviceResponse with result

        Raises:
            DeviceNotFoundError: If device not found
            MultipleDevicesError: If multiple devices match and first not set
            RuntimeError: For other errors
        """
        server_hosts = self.get_host_list(args.host)

        # First find the device
        device, server = find_device(
            server_hosts=server_hosts,
            id=args.id,
            bus=args.bus,
            desc=args.desc,
            first=args.first,
            serial=args.serial,
        )

        # Then perform the requested action
        local_devices = []
        match args.command:
            case "attach":
                logger.info(f"Attaching device {device.bus_id} from {server}")
                attach_device(device.bus_id, server)
                # Discover the local port for the attached device
                local_port = Port.get_port_by_remote_busid(
                    device.bus_id, server, retries=20
                )
                if local_port:
                    local_devices = local_port.local_devices
                    logger.info(
                        f"Device attached on local port {local_port.port} "
                        f"with devices: {local_devices}"
                    )
                else:
                    logger.warning(
                        "Local device files not found (may still be initializing)"
                    )
            case "detach":
                logger.info(f"Detaching device {device.bus_id} from {server}")
                detach_device(device.bus_id, server)

        return ClientDeviceResponse(
            status="success", data=device, server=server, local_devices=local_devices
        )

    def _send_response(
        self,
        client_socket: socket.socket,
        response: ClientDeviceResponse | ClientErrorResponse,
    ):
        """Send a JSON response to the client."""
        client_socket.sendall(response.model_dump_json().encode("utf-8") + b"\n")

    def _send_error_response(
        self,
        client_socket: socket.socket,
        status: Literal["error", "not_found", "multiple_matches"],
        message: str,
    ):
        """Send an error response to the client."""
        response = ClientErrorResponse(status=status, message=message)
        self._send_response(client_socket, response)

    def handle_client(self, client_socket: socket.socket, address):
        """Handle individual client connections."""
        try:
            data = client_socket.recv(1024).decode("utf-8")

            if not data:
                self._send_error_response(
                    client_socket, error_response, "Empty or invalid command"
                )
                return

            # Try to parse the request
            request_adapter = TypeAdapter(ClientDeviceRequest)
            try:
                request = request_adapter.validate_json(data)
            except ValidationError as e:
                self._send_error_response(
                    client_socket, error_response, f"Invalid request format: {str(e)}"
                )
                return

            logger.info(
                f"{request.command.capitalize()} request from {address}: {request}"
            )

            # Handle the device command
            response = self.handle_device_command(request)
            self._send_response(client_socket, response)

        except DeviceNotFoundError as e:
            logger.warning(f"Device not found for client {address}: {e}")
            self._send_error_response(client_socket, not_found_response, str(e))
        except MultipleDevicesError as e:
            logger.warning(f"Multiple devices matched for client {address}: {e}")
            self._send_error_response(client_socket, multiple_matches_response, str(e))
        except Exception as e:
            logger.error(f"Error handling client {address}: {e}")
            self._send_error_response(client_socket, error_response, str(e))

        finally:
            client_socket.close()

    def start(self):
        """Start the client service."""
        logger.debug(f"Starting client service on {self.host}:{self.port}")
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True

        logger.info(f"Client service listening on {self.host}:{self.port}")

        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                logger.debug(f"Client connected from {address}")
                client_thread = threading.Thread(
                    target=self.handle_client, args=(client_socket, address)
                )
                client_thread.start()
            except OSError:
                logger.debug("Client service socket closed")
                break

    def stop(self):
        """Stop the client service."""
        logger.info("Stopping client service")
        self.running = False
        if self.server_socket:
            self.server_socket.close()
