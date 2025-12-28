"""Pydantic models for client service socket communication."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .usbdevice import UsbDevice

CLIENT_PORT = 5056


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
