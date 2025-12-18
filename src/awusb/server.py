import logging
import os
import socket
import threading

from pydantic import TypeAdapter, ValidationError

from .api import (
    AttachRequest,
    AttachResponse,
    ErrorResponse,
    ListRequest,
    ListResponse,
)
from .usbdevice import UsbDevice, get_device, get_devices
from .utility import run_command

logger = logging.getLogger(__name__)


class CommandServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 5055):
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

    def handle_attach(
        self,
        args: AttachRequest,
    ) -> UsbDevice:
        """Handle the 'attach' command with optional arguments."""
        criteria = args.model_dump(exclude={"command", "detach"})
        logger.debug(f"Looking for device with criteria: {criteria}")
        device = get_device(**criteria)

        logger.info(f"Unbinding device {device.bus_id}")
        # Skip sudo if already root (common in containers)
        sudo_prefix = [] if os.getuid() == 0 else ["sudo"]
        run_command([*sudo_prefix, "usbip", "unbind", "-b", device.bus_id], check=False)

        if args.detach:
            logger.info(f"Device unbound: {device.bus_id} ({device.description})")
        else:
            logger.info(f"Binding device: {device.bus_id} ({device.description})")
            run_command([*sudo_prefix, "usbip", "bind", "-b", device.bus_id])
        return device

    def _send_response(
        self,
        client_socket: socket.socket,
        response: ListResponse | AttachResponse | ErrorResponse,
    ):
        """Send a JSON response to the client."""
        client_socket.sendall(response.model_dump_json().encode("utf-8") + b"\n")

    def handle_client(self, client_socket: socket.socket, address):
        """Handle individual client connections."""

        try:
            data = client_socket.recv(1024).decode("utf-8")

            if not data:
                response = ErrorResponse(
                    status="error", message="Empty or invalid command"
                )
                self._send_response(client_socket, response)
                return

            # Try to parse as either ListRequest or AttachRequest
            request_adapter = TypeAdapter(ListRequest | AttachRequest)
            try:
                request = request_adapter.validate_json(data)
            except ValidationError as e:
                response = ErrorResponse(
                    status="error", message=f"Invalid request format: {str(e)}"
                )
                self._send_response(client_socket, response)
                return

            if isinstance(request, ListRequest):
                logger.info(f"List request from {address}")
                result = self.handle_list()
                response = ListResponse(status="success", data=result)
                self._send_response(client_socket, response)

            elif isinstance(request, AttachRequest):
                action = "detach" if request.detach else "attach"
                logger.info(f"{action.capitalize()} request from {address}: {request}")
                result = self.handle_attach(args=request)
                response = AttachResponse(status="success", data=result)
                self._send_response(client_socket, response)

        except Exception as e:
            response = ErrorResponse(status="error", message=str(e))
            self._send_response(client_socket, response)

        finally:
            client_socket.close()

    def _respond_to_client(self, client_socket, response):
        self._send_response(client_socket, response)

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
