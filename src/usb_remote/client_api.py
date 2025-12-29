"""Pydantic models for client service socket communication."""

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .usbdevice import UsbDevice

CLIENT_SOCKET_PATH = "/tmp/usb-remote-client.sock"
CLIENT_SOCKET_PATH_SYSTEMD = "/run/usb-remote-client/usb-remote-client.sock"


def get_client_socket_path() -> str:
    """Get the appropriate socket path based on execution context.

    Returns:
        /run/usb-remote-client/usb-remote-client.sock when running as systemd service,
        /tmp/usb-remote-client.sock otherwise.
    """
    # Detect systemd service by checking for INVOCATION_ID environment variable
    # and verifying the runtime directory exists (created by systemd's RuntimeDirectory)
    if os.environ.get("INVOCATION_ID"):
        socket_dir = Path(CLIENT_SOCKET_PATH_SYSTEMD).parent
        # Check if the directory exists and is writable (systemd creates it)
        if socket_dir.exists() and os.access(socket_dir, os.W_OK):
            return CLIENT_SOCKET_PATH_SYSTEMD
        else:
            raise RuntimeError(
                f"Expected systemd runtime directory {socket_dir}"
                f" does not exist or is not writable."
            )
    return CLIENT_SOCKET_PATH


class StrictBaseModel(BaseModel):
    """Base model with strict validation - no extra fields allowed."""

    model_config = ConfigDict(extra="forbid")


attach_command = "attach"
detach_command = "detach"


class ClientDeviceRequest(StrictBaseModel):
    """Request to attach/detach a USB device via client service."""

    command: Literal["attach", "detach"]
    id: str | None = None
    bus: str | None = None
    serial: str | None = None
    desc: str | None = None
    first: bool = False
    host: str | None = None


class ClientDeviceResponse(StrictBaseModel):
    """Response to client attach/detach request."""

    status: Literal["success", "failure"]
    data: UsbDevice
    server: str
    local_devices: list[str] = []


error_response = "error"
not_found_response = "not_found"
multiple_matches_response = "multiple_matches"


class ClientErrorResponse(StrictBaseModel):
    """Error response from client service."""

    status: Literal["error", "not_found", "multiple_matches"]
    message: str
