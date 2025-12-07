[![CI](https://github.com/epics-containers/awusb/actions/workflows/ci.yml/badge.svg)](https://github.com/epics-containers/awusb/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/epics-containers/awusb/branch/main/graph/badge.svg)](https://codecov.io/gh/epics-containers/awusb)
[![PyPI](https://img.shields.io/pypi/v/awusb.svg)](https://pypi.org/project/awusb)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# awusb

Client-server software to share USB devices over the network.

Source          | <https://github.com/epics-containers/awusb>
:---:           | :---:
PyPI            | `pip install awusb`
Docker          | `docker run ghcr.io/epics-containers/awusb:latest`
Releases        | <https://github.com/epics-containers/awusb/releases>

## Documentation

- **[Quick Start Guide](docs/QUICKSTART.md)** - Get started from installation to first device share
- **[Architecture](docs/ARCHITECTURE.md)** - Understand the client-server model and design
- **[Raspberry Pi Setup](docs/RASBERRYPI.md)** - Guide to setting up a Raspberry Pi as a USB server

## Multi-Server Configuration

You can configure `awusb` to scan multiple USB device servers automatically. The client discovers configuration files in the following priority order:

1. **Environment variable**: `AWUSB_CONFIG=/path/to/config.yaml`
1. **Project-local config**: `.awusb.config` in current directory
1. **User config**: `~/.config/awusb/awusb.config` (default)

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

See `awusb.config.example` for a sample configuration file.

### Config File Discovery Examples

```bash
# Use default config from ~/.config/awusb/awusb.config
awusb list

# Use project-specific config from current directory
cd /path/to/project
echo "servers: [myserver]" > .awusb.config
awusb list

# Use environment variable (useful in CI/CD)
export AWUSB_CONFIG=/etc/awusb/production.config
awusb list
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

## Installing as a Service

You can install the awusb server as a systemd service to run automatically at boot.

### System Service (Recommended)

Install as a system service (runs at boot, before login):

```bash
# Install as system service (requires sudo)
sudo awusb install-service --system

# Enable and start
sudo systemctl enable awusb.service
sudo systemctl start awusb.service

# Check status
sudo systemctl status awusb.service
```

### User Service (Not Recommended)

Install as a user service (runs when you log in) useful for testing if you don't have sudo access:

```bash
# Install the service
awusb install-service

# Enable it to start on login
systemctl --user enable awusb.service

# Start the service now
systemctl --user start awusb.service

# Check status
systemctl --user status awusb.service

# View logs
journalctl --user -u awusb.service -f
```


### Uninstalling

```bash
# Uninstall user service
awusb uninstall-service

# Uninstall system service (requires sudo)
sudo awusb uninstall-service --system
```
