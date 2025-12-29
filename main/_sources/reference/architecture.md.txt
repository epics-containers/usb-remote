# Architecture

This document explains the architecture and design of usb-remote.

## Overview

usb-remote is a client-server system for sharing USB devices over a network using the USB/IP protocol. It provides a high-level Python interface with automatic device discovery across multiple servers.

It intentionally provides no security features, relying on network-level security instead. This makes it very simple to deploy and operate in controlled environments.

```
┌─────────────────────────────────────────────────────────────────┐
│                         usb-remote Architecture                 │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐                                  ┌──────────────┐
│              │         Network (TCP/IP)         │              │
│    Client    │◄────────────────────────────────►│    Server    │
│   Machine    │        Port 5055 (JSON)          │   Machine    │
│              │                                  │              │
└──────────────┘                                  └──────────────┘
      │                                                  │
      │ usbip attach/detach                              │ usbip bind
      │ (USB/IP kernel)                                  │ (USB/IP kernel)
      ▼                                                  ▼
┌──────────────┐                                  ┌──────────────┐
│   Virtual    │         USB/IP Protocol          │   Physical   │
│ USB Devices  │◄────────────────────────────────►│ USB Devices  │
│  (vhci-hcd)  │      Port 3240 (binary)          │   (ehci,     │
│              │                                  │    xhci...)  │
└──────────────┘                                  └──────────────┘
      │                                                   │
      ▼                                                   ▼
  Applications                                    Actual USB Hardware
  using devices                                   (cameras, Arduino, etc.)
```

## Components

### 1. Client (usb-remote CLI)

The client provides a user-friendly command-line interface for managing remote USB devices.

**Key Modules:**

- **`__main__.py`**: CLI entry point using Typer
  - Command parsing and validation
  - User interaction
  - Error handling and display

- **`client.py`**: Network communication
  - JSON-based protocol over TCP
  - Server discovery and querying
  - Multi-server support
  - Timeout handling

- **`config.py`**: Configuration management
  - YAML configuration files
  - File discovery (env, local, user config)
  - Pydantic validation
  - Server list management

- **`usbdevice.py`**: USB device abstraction
  - Device enumeration
  - Metadata extraction (vendor, product, serial)
  - Device filtering and matching

- **`utility.py`**: Helper functions
  - Subprocess execution
  - Error handling
  - Logging utilities

**Client Workflow:**

```
User Command
     │
     ▼
┌─────────────────┐
│  CLI Parser     │  Parse arguments
│  (Typer)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Config Loading  │  Discover & load config
│                 │  Get server list
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Server Query    │  Send JSON request to each server
│                 │  Collect responses
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Device Matching │  Filter devices by criteria
│                 │  Handle multiple matches
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ USB/IP Command  │  Execute usbip attach/detach
│                 │  Verify success
└────────┬────────┘
         │
         ▼
    Display Result
```

### 2. Server (usb-remote server)

The server runs on machines with USB devices to share, exposing them via a JSON API.

**Key Modules:**

- **`server.py`**: TCP server implementation
  - Socket handling
  - Request/response cycle
  - Error responses
  - Connection management

- **`usbdevice.py`**: Device enumeration (shared with client)
  - Queries local USB devices via `usbip list -l`
  - Extracts device metadata
  - Manages USB/IP binding

- **`service.py`**: Systemd integration
  - Service file generation
  - Installation/uninstallation
  - User vs. system service support

**Server Workflow:**

```
Server Start
     │
     ▼
┌─────────────────┐
│  Bind Socket    │  Listen on 0.0.0.0:5055
│                 │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Accept         │◄─── Wait for connections
│  Connection     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Receive        │  Read JSON request
│  Request        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Parse &        │  Validate using Pydantic
│  Validate       │
└────────┬────────┘
         │
         ├──────► list: Query local devices
         │              Return device list
         │
         ├──────► attach: Find device
         │                Return device details
         │
         ├──────► detach: Find device
         │                Return device details
         │
         ▼
┌─────────────────┐
│  Send Response  │  JSON response
│                 │
└────────┬────────┘
         │
         ▼
   Close Connection
         │
         └──────► Wait for next connection
```

### 3. Protocol (Pydantic Models)

Communication uses JSON messages validated by Pydantic models.

See [api.py](../../src/usb_remote/api.py) for full details.

### 4. USB/IP Layer

usb-remote leverages the Linux USB/IP kernel driver for actual device sharing.

**USB/IP Components:**

```
Client Side:
┌──────────────────────┐
│  vhci-hcd module     │  Virtual USB host controller
│                      │  Presents remote devices as local
└──────────────────────┘

Server Side:
┌──────────────────────┐
│  usbip-host module   │  Exports USB devices
│                      │  Binds physical devices to network
└──────────────────────┘

Protocol:
┌──────────────────────┐
│  USB/IP Protocol     │  Binary protocol on port 3240
│  (TCP, port 3240)    │  Tunnels USB traffic over network
└──────────────────────┘
```

**How usb-remote Uses USB/IP:**

1. **Server side:**
   - Lists devices: `usbip list -lp`
   - Binds device: `usbip bind -b <bus_id>`
   - Unbinds device: `usbip unbind -b <bus_id>`

2. **Client side:**
   - Attaches device: `sudo usbip attach -r <server> -b <bus_id>`
   - Detaches device: `sudo usbip detach -p <port>`
   - Lists attached: `usbip port`

## Configuration System

### Discovery Priority

2. **`usb-remote_CONFIG` env var**: Environment override
3. **`.usb-remote.config`**: Project-local config
4. **`~/.config/usb-remote/usb-remote.config`**: User default

### Configuration Model

```python
class usb-remoteConfig(BaseModel):
    servers: list[str] = []
    timeout: float = Field(default=5.0, gt=0)
```

Validated using Pydantic for type safety and constraints.

## Multi-Server Support

### List Command

Query all configured servers in parallel:

```
┌────────┐    ┌────────┐    ┌────────┐
│Server 1│    │Server 2│    │Server 3│
└───┬────┘    └───┬────┘    └───┬────┘
    │             │             │
    ◄─────────────┼─────────────┤ Client queries all
    │             │             │
    ├─────────────►             │
    │  Response   │             │
    │             ├─────────────►
    │             │  Response   │
    │             │             ├────────►
    │             │             │ Response
    │             │             │
    └─────────────┴─────────────┴────────────►
                                   Aggregate results
```

### Attach Command

Search servers sequentially until match found:

```
┌────────┐    ┌────────┐    ┌────────┐
│Server 1│    │Server 2│    │Server 3│
└───┬────┘    └───┬────┘    └───┬────┘
    │             │             │
    ◄─────────────┤             │ Query Server 1
    │  No match   │             │
    │             ◄─────────────┤ Query Server 2
    │             │   Match!    │ Found - stop searching
    │             ├─────────────►
    │             │             │
    │             │             │
    └─────────────┴─────────────┘
              Attach from Server 2
```

## Error Handling

### Layers of Error Handling

1. **Network Layer**: Connection timeouts, refused connections
2. **Protocol Layer**: Invalid JSON, schema validation
3. **Application Layer**: Device not found, multiple matches
4. **System Layer**: USB/IP command failures

### Error Flow

```
User Command
     │
     ▼
  Try Query
     │
     ├──► Network Error ──► Log warning, try next server
     │
     ├──► Timeout ──► Log warning, try next server
     │
     ├──► Server Error ──► Log error details
     │
     └──► Success ──► Process response
          │
          ├──► No match ──► Try next server
          │
          ├──► Multiple matches ──► Error (unless --first)
          │
          └──► Single match ──► Proceed
```

## Security Considerations

This project is a software replacement for AnywhereUSB, which is a commercial product designed for USB over IP sharing. It explicitly does not provide the  security features of the commercial product. This is to make it easy to deploy and operate in a controlled network environment where security can be managed at the network level.

**Key Points:**

- No authentication in base protocol (network security required)
- Requires root/sudo for USB/IP operations
- No encryption (use VPN for remote access)
