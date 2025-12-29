# Client Service Setup

The `client-service` command provides a Unix socket interface for attaching and detaching USB devices programmatically. This is useful when you want to integrate USB device attachment/detachment into other applications or services.

## Overview

The client service:
- Runs as a long-lived process (foreground or systemd service)
- Listens on a Unix socket for JSON commands
- Accepts `attach` and `detach` requests
- Returns JSON responses with device information and local device paths
- Automatically detects the appropriate socket path based on execution context:
  - `/run/usb-remote-client/usb-remote-client.sock` when running as a systemd service
  - `/tmp/usb-remote-client.sock` when running in foreground

## Running in Foreground

To run the client service directly in your terminal:

```bash
usb-remote client-service
```

This is useful for testing or development. The service will listen on `/tmp/usb-remote-client.sock`.

## Running as a Systemd Service

For production use, it's recommended to run the client service as a systemd service so it starts automatically at boot.

### Installation

#### System-wide Service (Recommended)

For speed and ease of use, you can install the client service using the `uv` tool as described below. However, if you prefer to use official package repositories, a good alternative is `pipx`. `pipx` allows you to install and run Python applications in isolated environments and is available on most Linux distributions.

1. Install `uv` (if not already installed).

    ```bash
    curl -LsSfO https://astral.sh/uv/install.sh
    sudo bash install.sh
    ```

2. Install the client service:

    ```bash
    sudo -s # uv (installed by root) requires the root profile so use sudo -s
    uvx usb-remote install-service --service-type client
    systemctl enable --now usb-remote-client.service
    exit
    ```

Check service status:

```bash
sudo systemctl status usb-remote-client.service
```

View service logs:

```bash
journalctl -u usb-remote-client.service -f
```


### Uninstallation

To uninstall the systemd service:

System-wide service:
```bash
sudo -s
uvx usb-remote uninstall-service client
exit
```

## Configuration

The client service uses the same configuration file format as the regular `usb-remote` client commands, see [Client Configuration File](../reference/config.md).

IMPORTANT: when running as a systemd service, the configuration file is read from the system-wide location:
`/etc/usb-remote-client/usb-remote.config`
