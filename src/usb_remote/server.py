import logging
import socket
import threading
from typing import Literal

from pydantic import TypeAdapter, ValidationError

from .api import (
    PORT,
    DeviceRequest,
    DeviceResponse,
    ErrorResponse,
    ListRequest,
    ListResponse,
    error_response,
    multiple_matches_response,
    not_found_response,
)
from .usbdevice import (
    DeviceNotFoundError,
    MultipleDevicesError,
    UsbDevice,
    get_device,
    get_devices,
)
from .utility import run_command

logger = logging.getLogger(__name__)


class CommandServer:
    def __init__(self, host: str = "0.0.0.0", port: int = PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False

    def handle_list(self) -> list[UsbDevice]:
        """Handle the 'list' command."""
        logger.debug("Retrieving list of USB devices")
        result = get_devices()
        logger.debug(f"Found {len(result)} USB devices")
        return result

    def attach(self, device: UsbDevice):
        """Attach (bind) the specified USB device."""
        logger.info(f"Binding device: {device.bus_id} ({device.description})")
        run_command(["sudo", "usbip", "bind", "-b", device.bus_id])
        logger.info(f"Device bound: {device.bus_id} ({device.description})")

    def detach(self, device: UsbDevice, check: bool = True):
        """Detach (unbind) the specified USB device."""
        logger.info(f"Unbinding device: {device.bus_id} ({device.description})")
        run_command(["sudo", "usbip", "unbind", "-b", device.bus_id], check=check)
        logger.info(f"Device unbound: {device.bus_id} ({device.description})")

    def handle_device(
        self,
        args: DeviceRequest,
    ) -> UsbDevice:
        """Handle the a device command with optional search criteria."""
        criteria = args.model_dump(exclude={"command"})
        logger.debug(f"Looking for device with criteria: {criteria}")
        device = get_device(**criteria)

        match args.command:
            case "attach":
                self.detach(device, check=False)
                self.attach(device)
            case "detach":
                self.detach(device)
            case "find":
                logger.info(f"Found device: {device.bus_id} ({device.description})")

        return device

    def _send_response(
        self,
        client_socket: socket.socket,
        response: ListResponse | DeviceResponse | ErrorResponse,
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
        response = ErrorResponse(status=status, message=message)
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

            # Try to parse as either ListRequest or AttachRequest
            request_adapter = TypeAdapter(ListRequest | DeviceRequest)
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

            if isinstance(request, ListRequest):
                result = self.handle_list()
                response = ListResponse(status="success", data=result)
                self._send_response(client_socket, response)

            elif isinstance(request, DeviceRequest):
                result = self.handle_device(args=request)
                response = DeviceResponse(status="success", data=result)
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
        """Start the server."""
        logger.debug(f"Starting server on {self.host}:{self.port}")
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True

        logger.info(f"Server listening on {self.host}:{self.port}")

        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                logger.debug(f"Client connected from {address}")
                client_thread = threading.Thread(
                    target=self.handle_client, args=(client_socket, address)
                )
                client_thread.start()
            except OSError:
                logger.debug("Server socket closed")
                break

    def stop(self):
        """Stop the server."""
        logger.info("Stopping server")
        self.running = False
        if self.server_socket:
            self.server_socket.close()
