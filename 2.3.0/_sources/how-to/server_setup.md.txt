# Server Setup

The server component of `usb-remote` runs on a machine with USB devices connected, and shares them over the network.

NOTE: There is no security in usb-remote server by design. It will share its USB devices with any client that asks for it. usb-remote is intended to be run in a trusted network environment only. Preferably isolated from the internet and any other devices. An instrumentation network at DLS is ideal.

## Recommended Hardware

Any linux machine with a supported USB controller can run the `usb-remote` server.

For good results and a pre-created image file with all the software installed, we recommend a Raspberry Pi 5, see [Recommended Server Hardware](../reference/recommended_hardware.md).

If you go with the recommended hardware, you can skip these instructions and instead go to the [Raspberry Pi Commissioning Guide](../tutorials/commissioning_raspi.md).

## Installing Prerequisites

1. Install the usbip CLI:

    ```bash
    sudo apt update
    sudo apt install usbip
    ```

2. Load the usbip kernel modules and ensure they load at boot:

    ```bash
    sudo modprobe usbip-core
    sudo modprobe usbip-host
    echo -e "usbip-core\nusbip-host" | sudo tee /etc/modules-load.d/usbip.conf
    ```

3. Create a service to run the usbipd daemon at boot:

    ```bash
    sudo tee /etc/systemd/system/usbipd.service > /dev/null <<EOF
    [Unit]
    Description=USB/IP Daemon
    After=network.target

    [Service]
    type=forking
    ExecStart=/usr/sbin/usbipd -D
    Restart=on-failure

    [Install]
    WantedBy=multi-user.target
    EOF

    sudo systemctl enable --now usbipd.service
    ```

## Installing usb-remote Server

A quick way to install the `usb-remote` server is via the `uv` tool.

1. Install `uv`.

    ```bash
    curl -LsSfO https://astral.sh/uv/install.sh
    sudo bash install.sh
    ```

1. Install `usb-remote` system service.

    ```bash
    sudo -s # uv (installed by root) requires the root profile so use sudo -s
    uvx usb-remote install-service server
    systemctl enable --now usb-remote
    exit
    ```

## Verify the Installation

1. Check the status of the `usbip` and `usb-remote` services:

    ```bash
    sudo systemctl status usbipd
    sudo systemctl status usb-remote
    ```

1. List the locally available USB devices:

    ```bash
    uvx usbip list --host localhost
    ```

The output should show the USB devices connected to the server machine (if any). e.g.

    ```bash
    $ uvx usb-remote list --host localhost

    === localhost ===
    - Cambridge Silicon Radio, Ltd Bluetooth Dongle (HCI mode)
    id=0a12:0001 bus=5-3.1.1
    - ZSA Technology Labs Voyager
    serial=pDAzE/lbjWze
    id=3297:1977 bus=5-3.1.2.1
    - Logitech, Inc. Unifying Receiver
    id=046d:c52b bus=5-3.1.2.2
    - Realtek Semiconductor Corp. BillBoard Device
    serial=123456789ABCDEFGH
    id=0bda:5400 bus=5-3.3.1
    - Texas Instruments, Inc. TUSB3410 Microcontroller
    serial=67085759
    id=0451:3410 bus=5-3.3.4
    - Genesys Logic, Inc. SD Card Reader and Writer
    serial=000000001206
    id=05e3:0749 bus=6-3.1.2.4
    (usb-remote)
    ```
