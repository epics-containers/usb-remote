[![CI](https://github.com/epics-containers/usb-remote/actions/workflows/ci.yml/badge.svg)](https://github.com/epics-containers/usb-remote/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/epics-containers/usb-remote/branch/main/graph/badge.svg)](https://codecov.io/gh/epics-containers/usb-remote)
[![PyPI](https://img.shields.io/pypi/v/usb-remote.svg)](https://pypi.org/project/usb-remote)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# usb-remote

Client-server software to share USB devices over the network.

Source          | <https://github.com/epics-containers/usb-remote>
:---:           | :---:
PyPI            | `pip install usb-remote`
Docker          | `docker run ghcr.io/epics-containers/usb-remote:latest`
Releases        | <https://github.com/epics-containers/usb-remote/releases>

## Documentation

- **[Quick Start Guide](docs/QUICKSTART.md)** - Get started from installation to first device share
- **[Architecture](docs/ARCHITECTURE.md)** - Understand the client-server model and design
- **[Raspberry Pi Setup](docs/RASBERRYPI.md)** - Guide to setting up a Raspberry Pi as a USB server

## Multi-Server Configuration

You can configure `usb-remote` to scan multiple USB device servers automatically. The client discovers configuration files in the following priority order:

1. **Environment variable**: `USB_REMOTE_CONFIG=/path/to/config.yaml`
1. **Project-local config**: `.usb-remote.config` in current directory
1. **User config**: `~/.config/usb-remote/usb-remote.config` (default)

Create a configuration file with the following format:

```yaml
servers:
  - localhost
  - raspberrypi
  - 192.168.1.100
  - usb-server-1.local

# Optional: Connection timeout in seconds (default: 5.0)
timeout: 5.0
```

See `usb-remote.config.example` for a sample configuration file.

### Config File Discovery Examples

```bash
# Use default config from ~/.config/usb-remote/usb-remote.config
usb-remote list

# Use project-specific config from current directory
cd /path/to/project
echo "servers: [myserver]" > .usb-remote.config
usb-remote list

# Use environment variable (useful in CI/CD)
export USB_REMOTE_CONFIG=/etc/usb-remote/production.config
usb-remote list
```

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
usb-remote list

# List devices on a specific server
usb-remote list --host raspberrypi

# Attach a device (scans all servers, fails if multiple matches)
usb-remote attach --desc "Camera"

# Attach first matching device across servers
usb-remote attach --desc "Camera" --first

# Attach a device from a specific server
usb-remote attach --desc "Camera" --host 192.168.1.100

# Detach with first match (if same device attached from multiple servers)
usb-remote detach --desc "Camera" --first
```

## Installing as a Service

You can install the usb-remote server as a systemd service to run automatically at boot.

### System Service (Recommended)

Install as a system service (runs at boot, before login):

```bash
# Install as system service (requires sudo)
sudo usb-remote install-service --system

# Enable and start
sudo systemctl enable usb-remote.service
sudo systemctl start usb-remote.service

# Check status
sudo systemctl status usb-remote.service
```

### User Service (Not Recommended)

Install as a user service (runs when you log in) useful for testing if you don't have sudo access:

```bash
# Install the service
usb-remote install-service

# Enable it to start on login
systemctl --user enable usb-remote.service

# Start the service now
systemctl --user start usb-remote.service

# Check status
systemctl --user status usb-remote.service

# View logs
journalctl --user -u usb-remote.service -f
```


### Uninstalling

```bash
# Uninstall user service
usb-remote uninstall-service

# Uninstall system service (requires sudo)
sudo usb-remote uninstall-service --system
```
