# Client Configuration File

The client configuration determines which USB device servers the `usb-remote` client will attempt to connect to.

## Configuration via the CLI

You can specify a configuration file directly using the `config` command with any `usb-remote` command:

see help for details:
```bash
usb-remote config --help
```

## File Location Priority

The client discovers configuration files in the following priority order:

1. **Environment variable**: `USB_REMOTE_CONFIG=/path/to/config.yaml`
1. **Project-local config**: `.usb-remote.config` in current directory
1. **User config**: `~/.config/usb-remote/usb-remote.config` (default)

## File Format

Create a configuration file with the following YAML format:

```yaml

# list of USB device servers: DNS names or IP addresses
servers:
  - raspberrypi
  - 192.168.1.100
  - usb-server-1.local

# IP ranges to scan for servers (last octet only)
server_ranges:
  - 192.168.2.31-36  # Scans 192.168.2.31 through 192.168.2.36
  - 192.168.1.50-60  # Scans 192.168.1.50 through 192.168.1.60

# Optional: Connection timeout in seconds (default: 5.0)
timeout: 5.0
```

### Server Discovery

The client will connect to servers from two sources:

1. **Static servers**: Listed explicitly in the `servers` section
2. **Dynamic discovery**: IP ranges in `server_ranges` are scanned to find servers listening on port 5055

Server ranges use shorthand notation specifying only the last octet:
- Format: `192.168.2.31-36` scans from `.31` through `.36`
- This keeps scans fast by limiting range to a single subnet segment

See [usb-remote.config.example](../../usb-remote.config.example) for a sample configuration file.
