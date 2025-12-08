# Raspberry Pi

## Intro

The Raspberry Pi make a great low-cost USB server. It has multiple USB ports and built-in network connectivity.

A 4GB (or more) Raspberry Pi 4 or Raspberry Pi 5 is recommended for best performance.

Power over Ethernet (PoE) is a nice to have for clean cabling.

TODO: suggestions for cooling.

## Quick Setup

TODO: we will provice a pre-built iso image for Raspberry Pi OS with awusb server and pre-installed.

## Install Raspberry Pi OS

1. Install Raspberry Pi OS Lite (although if you need to use Wifi, the Full version is much easier) on your Raspberry Pi.
   - Follow the official Raspberry Pi documentation for installation instructions. at https://www.raspberrypi.com/documentation/computers/getting-started.html#raspberry-pi-imager
2. Create a user account and set up SSH access.
3. Install packages and kernel modules:
    ```bash
    sudo -s

    apt update; apt upgrade -y
    apt install -y usbip vim fswebcam

    sudo modprobe usbip_core
    sudo modprobe usbip_host
    echo usbip_core >> /etc/modules
    echo usbip_host >> /etc/modules
    ```
4. Setup usbip daemon as a system service with
    - `vim /etc/systemd/system/usbipd.service`

    Then add the following content to `usbipd.service`:
    ```ini
    [Unit]
    Description=Usbipd
    After=network.target

    [Service]
    Type=forking
    ExecStart=/usr/sbin/usbipd -D

    [Install]
    WantedBy=multi-user.target
    ```

5. Enable and start the usbipd service:
    ```bash
    sudo systemctl enable usbipd --now
    ```

6. Install uv as root using https://docs.astral.sh/uv/getting-started/installation/#installation-methods

7. Install awusb server as a system service:
    ```bash
    sudo -s
    uvx awusb install-service --system
    systemctl enable awusb.service --now
    exit
    ```
Thats it. Now add your new Raspberry Pi server to your awusb client configuration and start sharing USB devices:

```bash
awusb config add-server <your new raspberrypi ip or hostname>
```
