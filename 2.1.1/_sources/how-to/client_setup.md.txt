# Client Setup

The client component of `usb-remote` runs on a machine that wants to access USB devices shared over the network by one or more `usb-remote` servers.

## Recommended Hardware

Any linux machine with access to the usbip CLI can run the `usb-remote` client. Windows and MacOS are not tested yet, but as the project is written in Python and just calls out to the usbip CLI, it should be able to run on those platforms as well.

## Installing Prerequisites

1. Install the usbip CLI:

    ```bash
    sudo apt update
    sudo apt install usbip
    ```
2. Load the vhci-hcd kernel module and ensure it loads at boot:

    ```bash
    sudo modprobe vhci-hcd
    echo "vhci-hcd" | sudo tee /etc/modules-load.d/vhci.conf
    ```

## Installing usb-remote Client

A quick way to install the `usb-remote` client is via the `uv` tool.

1. Install `uv`.

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    cd; source .bashrc
    ```

1. Run the client using uvx:

    ```bash
    uvx usb-remote --help
    ```

## Verify the Installation

Assuming you have at least one `usb-remote` server running on your network, you can verify the client installation by listing available USB devices:

```bash
usb-remote config add-server <server_address>
usb-remote list
```
