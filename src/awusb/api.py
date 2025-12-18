"""Pydantic models for client-server communication."""

from typing import Literal

from pydantic import BaseModel

from .usbdevice import UsbDevice


class StrictBaseModel(BaseModel):
    """Base model with strict validation - no extra fields allowed."""

    class Config:
        extra = "forbid"


class ListRequest(StrictBaseModel):
    """Request to list available USB devices."""

    command: Literal["list"] = "list"


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


class ErrorResponse(StrictBaseModel):
    """Error response."""

    status: Literal["error"]
    message: str
