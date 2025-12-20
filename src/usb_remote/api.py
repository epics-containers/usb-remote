"""Pydantic models for client-server communication."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .usbdevice import UsbDevice

PORT = 5055


class StrictBaseModel(BaseModel):
    """Base model with strict validation - no extra fields allowed."""

    model_config = ConfigDict(extra="forbid")


class ListRequest(StrictBaseModel):
    """Request to list available USB devices."""

    command: Literal["list"] = "list"


find_command = "find"
attach_command = "attach"
detach_command = "detach"


class DeviceRequest(StrictBaseModel):
    """Request to find/attach/detach a USB device."""

    command: Literal["find", "attach", "detach"]
    id: str | None = None
    bus: str | None = None
    serial: str | None = None
    desc: str | None = None
    first: bool = False


class ListResponse(StrictBaseModel):
    """Response containing list of USB devices."""

    status: Literal["success"]
    data: list[UsbDevice]


class DeviceResponse(StrictBaseModel):
    """Response to attach request."""

    status: Literal["success", "failure"]
    data: UsbDevice


error_response = "error"
not_found_response = "not_found"
multiple_matches_response = "multiple_matches"


class ErrorResponse(StrictBaseModel):
    """Error response."""

    status: Literal["error", "not_found", "multiple_matches"]
    message: str
