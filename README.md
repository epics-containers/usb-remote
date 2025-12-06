[![CI](https://github.com/epics-containers/awusb/actions/workflows/ci.yml/badge.svg)](https://github.com/epics-containers/awusb/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/epics-containers/awusb/branch/main/graph/badge.svg)](https://codecov.io/gh/epics-containers/awusb)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# awusb

a container that mounts remote devices locally using anywhereusb

Source          | <https://github.com/epics-containers/awusb>
:---:           | :---:
Docker          | `docker run ghcr.io/epics-containers/awusb:latest`
Releases        | <https://github.com/epics-containers/awusb/releases>

## Multi-Server Configuration

You can configure `awusb` to scan multiple USB device servers automatically. Create a configuration file at `~/.config/awusb/awusb.config`:

```yaml
servers:
  - localhost
  - raspberrypi
  - 192.168.1.100
  - usb-server-1.local

# Optional: Connection timeout in seconds (default: 5.0)
timeout: 5.0
```

See `awusb.config.example` for a sample configuration file.

### Connection Timeout

The `timeout` setting controls how long to wait when connecting to each server before giving up. This prevents the client from hanging when a server is unreachable. The default is 5 seconds, but you can adjust it based on your network conditions:

- **Fast local network**: Use a shorter timeout (e.g., `2.0` seconds)
- **Slow or remote servers**: Use a longer timeout (e.g., `10.0` seconds)

When a server times out, it's logged as a warning and skipped, allowing other servers to be queried.

### Behavior

- **list**: Without `--host`, queries all configured servers and displays devices grouped by server
- **attach/detach**: Without `--host`, scans all servers to find a matching device
  - Fails if no match is found across all servers
  - Fails if multiple matches are found across different servers (unless `--first` is used)
  - Succeeds if exactly one match is found (reports which server it was found on)
  - With `--first` flag: Attaches the first matching device found, even if multiple servers have matching devices
- **--host flag**: When specified, only queries that specific server (ignores config file)

### Examples

```bash
# List devices on all configured servers
awusb list

# List devices on a specific server
awusb list --host raspberrypi

# Attach a device (scans all servers, fails if multiple matches)
awusb attach --desc "Camera"

# Attach first matching device across servers
awusb attach --desc "Camera" --first

# Attach a device from a specific server
awusb attach --desc "Camera" --host 192.168.1.100

# Detach with first match (if same device attached from multiple servers)
awusb detach --desc "Camera" --first
```
