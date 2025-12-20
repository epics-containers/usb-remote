# USB_REMOTE Quick Start Guide

This guide will help you get started with USB_REMOTE, from installation to sharing your first USB device over the network.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [First-Time Setup](#first-time-setup)
- [Server Setup](#server-setup)
- [Client Setup](#client-setup)
- [Your First Device Share](#your-first-device-share)
- [Next Steps](#next-steps)

## Prerequisites

### Server Requirements

- Linux system with USB devices you want to share
- `usbip` kernel module and tools installed
- Python 3.11 or later
- Network connectivity

### Client Requirements

- Linux system that will access remote USB devices
- `usbip` tools installed
- Python 3.11 or later
- Network access to the server

### Installing usbip

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install linux-tools-generic hwdata
```

**Fedora/RHEL:**
```bash
sudo dnf install usbip
```

**Arch Linux:**
```bash
sudo pacman -S usbip
```

**Load the kernel module:**
```bash
# Load immediately
sudo modprobe vhci-hcd

# Make it permanent (load on boot)
echo "vhci-hcd" | sudo tee /etc/modules-load.d/usbip.conf
```

## Installation

### Install from PyPI (Recommended)

```bash
# Create a virtual environment (recommended)
python -m venv ~/.venv/usb-remote
source ~/.venv/usb-remote/bin/activate

# Install usb-remote
pip install usb-remote

# Verify installation
usb-remote --version
```

### Install from Source

```bash
git clone https://github.com/epics-containers/usb-remote.git
cd usb-remote
pip install -e .
```

### Install as System Package

For system-wide installation:

```bash
sudo pip install usb-remote
```

## First-Time Setup

### Server Setup

The server is the machine with USB devices you want to share.

#### 1. Verify USB Devices

Check what USB devices are available:

```bash
usb-remote list -l
```

You should see a list like:
```
- USB Camera
  id=0c45:6340 bus=1-2.3
  serial=SN12345

- Arduino Uno
  id=2341:0043 bus=1-4.1
```

#### 2. Start the Server

**Option A: Run directly (for testing)**

```bash
usb-remote server
```

The server runs on port 5055 by default.

**Option B: Install as a systemd service (recommended for production)**

NOTE: a user service only has limited access to device parameters e.g. serial numbers are not usually available. This makes a user service very poor for environments where multiple identical devices are connected.

```bash
# Install as user service
usb-remote install-service

# Enable to start on login
systemctl --user enable usb-remote.service

# Start the service
systemctl --user start usb-remote.service

# Check status
systemctl --user status usb-remote.service
```

For system-wide installation (starts at boot):

We recommend installing like this in an isolated 'instrumentation' network.

```bash
sudo usb-remote install-service --system
sudo systemctl enable usb-remote.service
sudo systemctl start usb-remote.service
```

#### 3. Verify Server is Running

From another terminal:

```bash
# If running locally
usb-remote list --host localhost

# From another machine (replace with server's IP)
usb-remote list --host 192.168.1.100
```

### Client Setup

The client is the machine that will access remote USB devices.

#### 1. Create Configuration File

Create a configuration file to specify your servers:

```bash
# Create config directory
mkdir -p ~/.config/usb-remote

# Create config file
cat > ~/.config/usb-remote/usb-remote.config << EOF
servers:
  - localhost
  - 192.168.1.100
  - usb-server-1.local

timeout: 5.0
EOF
```

Or use the CLI:

```bash
# Add servers one at a time
usb-remote config add-server 192.168.1.100
usb-remote config add-server usb-server-1.local

# Set timeout
usb-remote config set-timeout 5.0

# View current config
usb-remote config show
```

#### 2. Test Connectivity

List devices from all configured servers:

```bash
usb-remote list
```

You should see output grouped by server:

```
Server: 192.168.1.100
- USB Camera
  id=0c45:6340 bus=1-2.3
  serial=SN12345

Server: usb-server-1.local
- Arduino Uno
  id=2341:0043 bus=1-4.1
```

## Your First Device Share

### Step 1: Find Your Device

List all available devices:

```bash
usb-remote list
```

Identify the device you want to attach by its description, serial number, or ID.

### Step 2: Attach the Device

**Attach by description:**

```bash
usb-remote attach --desc "Camera"
```

**Attach by serial number (most specific):**

```bash
usb-remote attach --serial SN12345
```

**Attach by vendor:product ID:**

```bash
usb-remote attach --id 0c45:6340
```

**Attach by bus ID (from a specific server):**

```bash
usb-remote attach --bus 1-2.3 --host 192.168.1.100
```

### Step 3: Verify the Device is Attached

Check local USB devices:

```bash
lsusb
```

You should see the remote device as if it were connected locally.

### Step 4: Use the Device

The device now appears as a local USB device and can be used by any application:

```bash
# Camera example
ls /dev/video*

# Serial device example
ls /dev/ttyUSB* /dev/ttyACM*

# Open in your application
cheese  # for camera
arduino # for Arduino
```

### Step 5: Detach When Done

Detach the device when you're finished:

```bash
# By description
usb-remote detach --desc "Camera"

# By serial
usb-remote detach --serial SN12345

# By ID
usb-remote detach --id 0c45:6340
```

## Next Steps

### Multiple Servers

If you have devices on multiple servers:

```bash
# List shows devices from all servers
usb-remote list

# Attach automatically finds the device on any server
usb-remote attach --serial SN12345

# Use --first if multiple servers have matching devices
usb-remote attach --desc "Camera" --first
```

### Project-Specific Configuration

Create a `.usb-remote.config` file in your project directory:

```bash
cd /path/to/project
cat > .usb-remote.config << EOF
servers:
  - test-server-1
  - test-server-2
timeout: 10.0
EOF

# Now commands in this directory use this config
usb-remote list
```

### Advanced Usage

**Using environment variables:**

```bash
export USB_REMOTE_CONFIG=/etc/usb-remote/production.config
usb-remote list
```

**Override timeout per command:**

```bash
usb-remote list --host slow-server --timeout 15.0
```

**Debug logging:**

```bash
usb-remote --debug list
usb-remote --debug attach --desc "Camera"
```

### Monitoring

**View server logs:**

```bash
# User service
journalctl --user -u usb-remote.service -f

# System service
sudo journalctl -u usb-remote.service -f
```

**Check service status:**

```bash
# User service
systemctl --user status usb-remote.service

# System service
sudo systemctl status usb-remote.service
```

## Common Issues

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed troubleshooting steps.

**Quick fixes:**

- **"Permission denied" errors**: Run with `sudo` or add your user to appropriate groups
- **Connection timeouts**: Check firewall, increase timeout in config
- **Device not found**: Verify server is running, check network connectivity
- **Multiple matches**: Use more specific criteria (`--serial` instead of `--desc`)

## Getting Help

- Documentation: See `docs/` directory
- Issues: <https://github.com/epics-containers/usb-remote/issues>
- Security: See [SECURITY.md](SECURITY.md)
