"""Pydantic models for client-server communication."""

from typing import Literal

from pydantic import BaseModel

from .usbdevice import UsbDevice


class ListRequest(BaseModel):
    """Request to list available USB devices."""

    command: Literal["list"] = "list"


class AttachRequest(BaseModel):
    """Request to attach a USB device."""

    command: Literal["attach"] = "attach"
    id: str | None = None
    bus: str | None = None
    serial: str | None = None
    desc: str | None = None


class ListResponse(BaseModel):
    """Response containing list of USB devices."""

    status: Literal["success"]
    data: list[UsbDevice]


class AttachResponse(BaseModel):
    """Response to attach request."""

    status: Literal["success", "failure"]


class ErrorResponse(BaseModel):
    """Error response."""

    status: Literal["error"]
    message: str
