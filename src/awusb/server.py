import socket
import threading

from pydantic import TypeAdapter, ValidationError

from .models import (
    AttachRequest,
    AttachResponse,
    ErrorResponse,
    ListRequest,
    ListResponse,
)
from .usbdevice import UsbDevice, get_devices


class CommandServer:
    def __init__(self, host: str = "localhost", port: int = 5000):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False

    def handle_list(self) -> list[UsbDevice]:
        """Handle the 'list' command."""
        # TODO: Implement list logic
        result = get_devices()
        return result

    def handle_attach(
        self,
        args: AttachRequest,
    ) -> bool:
        """Handle the 'attach' command with optional arguments."""
        # TODO: Implement attach logic

        return True

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
                print(f"List from: {address}")
                result = self.handle_list()
                response = ListResponse(status="success", data=result)
                self._send_response(client_socket, response)

            elif isinstance(request, AttachRequest):
                print(f"Attach from : {address}, args: {request}")
                result = self.handle_attach(args=request)
                response = AttachResponse(status="success" if result else "failure")
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
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True

        print(f"Server listening on {self.host}:{self.port}")

        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client, args=(client_socket, address)
                )
                client_thread.start()
            except OSError:
                break

    def stop(self):
        """Stop the server."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
