
# Client Service Socket API

The client service accepts JSON requests on the Unix socket and returns JSON responses.

## Request Format

All requests follow this JSON structure:

```json
{
  "command": "attach",
  "id": "1-1.4",
  "bus": null,
  "serial": null,
  "desc": null,
  "first": false,
  "host": null
}
```

**Fields:**
- `command`: Either `"attach"` or `"detach"` (required)
- `id`: Bus ID of the device (e.g., "1-1.4")
- `bus`: Bus number filter
- `serial`: Serial number filter
- `desc`: Description filter (substring match)
- `first`: If true, use first matching device if multiple matches
- `host`: Specific server hostname/IP to query (if null, queries all configured servers)

You must provide at least one of: `id`, `bus`, `serial`, or `desc` to identify the device.

## Response Format

### Success Response

```json
{
  "status": "success",
  "data": {
    "bus_id": "1-1.4",
    "device_id": "vid=0x1234 pid=0x5678",
    "description": "USB Device Description"
  },
  "server": "192.168.1.100",
  "local_devices": ["/dev/ttyUSB0", "/dev/ttyUSB1"]
}
```

**Fields:**
- `status`: Always `"success"` for successful operations
- `data`: The USB device information
  - `bus_id`: The USB bus ID on the remote server
  - `device_id`: Vendor and product IDs
  - `description`: Human-readable device description
- `server`: The server hostname/IP where the device was found
- `local_devices`: List of local device files created (for attach operations)

### Error Response

```json
{
  "status": "error",
  "message": "Error description"
}
```

**Status values:**
- `"error"`: General error (invalid request, connection error, etc.)
- `"not_found"`: No device matching the criteria was found
- `"multiple_matches"`: Multiple devices matched and `first` was not set to `true`

## Usage Examples

### Using netcat

Attach a device:
```bash
echo '{"command":"attach","desc":"Arduino","first":true}' | nc -U /tmp/usb-remote-client.sock
```

Detach a device by bus ID:
```bash
echo '{"command":"detach","id":"1-1.4"}' | nc -U /tmp/usb-remote-client.sock
```

### Using Python

```python
import json
import socket

# Connect to the client service socket
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect("/tmp/usb-remote-client.sock")

# Send attach request
request = {
    "command": "attach",
    "desc": "Arduino",
    "first": True
}
sock.sendall(json.dumps(request).encode() + b'\n')

# Receive response
response = sock.recv(4096).decode()
result = json.loads(response)

if result["status"] == "success":
    print(f"Attached device: {result['data']['description']}")
    print(f"Local devices: {result['local_devices']}")
else:
    print(f"Error: {result['message']}")

sock.close()
```

### Using curl (with socat)

You can use `socat` to create a bridge between HTTP and the Unix socket for testing:

```bash
# Terminal 1: Start socat bridge
socat TCP-LISTEN:8080,reuseaddr,fork UNIX-CONNECT:/tmp/usb-remote-client.sock

# Terminal 2: Send requests via HTTP
curl -X POST http://localhost:8080 -d '{"command":"attach","desc":"Arduino","first":true}'
```

## See Also

- [Client Service Socket API](client_service_api.md) - Client service API documentation
- [Server Setup](../how-to/server_setup.md) - Server installation and configuration
- [Architecture](architecture.md) - System architecture overview
