[![CI](https://github.com/epics-containers/usb-remote/actions/workflows/ci.yml/badge.svg)](https://github.com/epics-containers/usb-remote/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/epics-containers/usb-remote/branch/main/graph/badge.svg)](https://codecov.io/gh/epics-containers/usb-remote)
[![PyPI](https://img.shields.io/pypi/v/usb-remote.svg)](https://pypi.org/project/usb-remote)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# usb-remote

Client-server software to share USB devices over the network.

Source          | <https://github.com/epics-containers/usb-remote>
:---:           | :---:
PyPI            | `uvx usb-remote --version`
Docker          | `docker run ghcr.io/epics-containers/usb-remote:latest`
Documentation   | <https://epics-containers.github.io/usb-remote>
Releases        | <https://github.com/epics-containers/usb-remote/releases>


## Overview

`usb-remote` allows USB devices to be easily discovered and shared over a network using the USB/IP USB-over-Ethernet service.

A `usb-remote` server runs on a machine with physical USB devices attached and shares its devices to clients. Clients can connect to multiple servers to access and control their USB devices as if they were locally connected.

## Comparison to Digi's AnyWhereUSB

`usb-remote` is a FOSS alternative to commercial USB-over-Ethernet solutions like Digi's AnyWhereUSB.

Advantages of Digi's AnyWhereUSB:
- Commercial product with support and warranty
- Dedicated hardware servers for USB device sharing
- Excellent security features controlling access to USB devices

Advantages of `usb-remote`:
- Good support for UVC isochronous Webcams that do not work with AnyWhereUSB
- Very simple to setup and use in trusted network environments
- Free and open source software (FOSS)
- The server runs on standard hardware such as a $55 Raspberry Pi

## Installation

See the [Server Setup](./how-to/server_setup.md) and [Client Setup](./how-to/client_setup.md) guides for installation instructions.

## Example Client Commands

```bash
# List devices on all configured servers
usb-remote list

# List devices on a specific server
usb-remote list --host raspberrypi1

# Attach a device my description substring
# (scans all servers, fails on multiple matches)
usb-remote attach --desc "Camera"

# Attach first matching device across servers
usb-remote attach --desc "Camera" --first

# Attach a device based on serial number - recommended to guarantee unique match
usb-remote attach --serial=1272D8DF

# Detach a device
usb-remote detach --serial=1272D8DF

# Find devices on the 1-4 bus of a specific server, using a glob pattern
usb-remote list --host raspberrypi1 --bus '1-4-*'
```

Search Arguments:
- `--desc TEXT` : substring or glob pattern to match device description
- `--serial TEXT` : glob pattern to match device serial number
- `--bus TEXT` : glob pattern to match USB bus ID (e.g. `1-4.3`)
- `--host TEXT` : search a single server by hostname or IP address

## Architecture

See the [Architecture Reference](./reference/architecture.md) for full details.

<!-- README only content. Anything below this line won't be included in index.md -->

See https://epics-containers.github.io/usb-remote for more detailed documentation.
