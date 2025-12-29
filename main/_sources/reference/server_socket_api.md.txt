
# Server Socket API

The server accepts JSON requests on a TCP socket (default port 5055) and returns JSON responses.

## Connection

The server listens on TCP port **5055** by default on all interfaces (0.0.0.0).

```python
import socket

# Connect to the server
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("server_hostname", 5055))
```

## Request Formats

### List Request

Request a list of all available USB devices on the server:

```json
{
  "command": "list"
}
```

**Fields:**
- `command`: Must be `"list"`

### Device Request

Request to find, attach, or detach a specific USB device:

```json
{
  "command": "attach",
  "id": "1-1.4",
  "bus": null,
  "serial": null,
  "desc": null,
  "first": false
}
```

**Fields:**
- `command`: Either `"find"`, `"attach"`, or `"detach"` (required)
- `id`: Bus ID of the device (e.g., "1-1.4")
- `bus`: Bus number filter
- `serial`: Serial number filter
- `desc`: Description filter (substring match)
- `first`: If true, use first matching device if multiple matches

You must provide at least one of: `id`, `bus`, `serial`, or `desc` to identify the device.

**Commands:**
- `"find"`: Locate a device without attaching or detaching it
- `"attach"`: Bind the device to usbip for sharing (makes it available for client attachment)
- `"detach"`: Unbind the device from usbip (makes it unavailable for sharing)

## Response Formats

### List Response

```json
{
  "status": "success",
  "data": [
    {
      "bus_id": "1-1.4",
      "device_id": "vid=0x1234 pid=0x5678",
      "description": "Arduino Uno"
    },
    {
      "bus_id": "1-1.5",
      "device_id": "vid=0x2341 pid=0x0043",
      "description": "Arduino Mega"
    }
  ]
}
```

**Fields:**
- `status`: Always `"success"` for successful list operations
- `data`: Array of USB device objects
  - `bus_id`: The USB bus ID on the server
  - `device_id`: Vendor and product IDs
  - `description`: Human-readable device description

### Device Response

```json
{
  "status": "success",
  "data": {
    "bus_id": "1-1.4",
    "device_id": "vid=0x1234 pid=0x5678",
    "description": "Arduino Uno"
  }
}
```

**Fields:**
- `status`: `"success"` for successful operations, `"failure"` for failed operations
- `data`: The USB device information
  - `bus_id`: The USB bus ID on the server
  - `device_id`: Vendor and product IDs
  - `description`: Human-readable device description

### Error Response

```json
{
  "status": "error",
  "message": "Error description"
}
```

**Status values:**
- `"error"`: General error (invalid request, command execution error, etc.)
- `"not_found"`: No device matching the criteria was found
- `"multiple_matches"`: Multiple devices matched and `first` was not set to `true`

## Usage Examples

### Using netcat

List all devices:
```bash
echo '{"command":"list"}' | nc server_hostname 5055
```

Find a device by description:
```bash
echo '{"command":"find","desc":"Arduino","first":true}' | nc server_hostname 5055
```

Attach a device (make it available for sharing):
```bash
echo '{"command":"attach","id":"1-1.4"}' | nc server_hostname 5055
```

Detach a device (make it unavailable for sharing):
```bash
echo '{"command":"detach","id":"1-1.4"}' | nc server_hostname 5055
```

### Using Python

```python
import json
import socket

def send_request(host: str, port: int, request: dict) -> dict:
    """Send a request to the server and return the response."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    # Send request
    sock.sendall(json.dumps(request).encode() + b'\n')

    # Receive response
    response = sock.recv(4096).decode()
    sock.close()

    return json.loads(response)

# List all devices
response = send_request("server_hostname", 5055, {"command": "list"})
if response["status"] == "success":
    print("Available devices:")
    for device in response["data"]:
        print(f"  - {device['description']} ({device['bus_id']})")

# Attach a device
response = send_request(
    "server_hostname",
    5055,
    {"command": "attach", "desc": "Arduino", "first": True}
)
if response["status"] == "success":
    print(f"Attached device: {response['data']['description']}")
    print(f"Bus ID: {response['data']['bus_id']}")
else:
    print(f"Error: {response['message']}")

# Detach a device
response = send_request(
    "server_hostname",
    5055,
    {"command": "detach", "id": "1-1.4"}
)
if response["status"] == "success":
    print(f"Detached device: {response['data']['description']}")
```

### Using curl (with socat)

You can use `socat` to create a bridge between HTTP and the TCP socket for testing:

```bash
# Terminal 1: Start socat bridge
socat TCP-LISTEN:8080,reuseaddr,fork TCP:server_hostname:5055

# Terminal 2: Send requests via HTTP
curl -X POST http://localhost:8080 -d '{"command":"list"}'
curl -X POST http://localhost:8080 -d '{"command":"attach","desc":"Arduino","first":true}'
```

## See Also

- [Client Service Socket API](client_service_api.md) - Client service API documentation
- [Server Setup](../how-to/server_setup.md) - Server installation and configuration
- [Architecture](architecture.md) - System architecture overview
