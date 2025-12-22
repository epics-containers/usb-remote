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

# Optional: Connection timeout in seconds (default: 5.0)
timeout: 5.0
```

See [usb-remote.config.example](../../usb-remote.config.example) for a sample configuration file.
