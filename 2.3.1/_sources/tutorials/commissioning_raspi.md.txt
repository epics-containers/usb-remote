# Commissioning a new Raspberry Pi as a usb-remote Server

## Introduction

Choosing the recommended hardware for a usb-remote server simplifies commissioning as there is a pre-built disk image available that includes all necessary software and configuration.


## Step 1: Obtain and Assemble Recommended Hardware

See [Recommended Server Hardware](../reference/recommended_hardware.md).

Any Raspberry Pi 4 or 5 with at least 4GB RAM and at least 16GB microSD card is suitable.

## Step 2: Flash the Raspberry Pi usb-remote Server Image

If you do not already have a pre-configured Raspberry Pi usb-remote server image, follow these steps to flash the image to a microSD card.

1. Download [raspi-lite-usb-remote-2.2.2.img on Google Drive][raspiImageLink]
  - Note: this image works for both Raspberry Pi 4 and Raspberry Pi 5.
  - TODO: make a separate image for DLS with different user/password and create a central supply of duplicates.

1. Insert a microSD card of at least 16GB capacity into a card reader connected to your computer.

1. Use `lsblk` to identify the device name of the microSD card (e.g. `/dev/sdb`).

1. Flash the image to a microSD card as follows. **CAREFUL** - replace `/dev/sdX` with the correct device name for your microSD card and remember that this will overwrite the specified device.
    ```bash
    sudo dd if=./raspi-lite-usb-remote-2.1.0.img of=/dev/sdX bs=4M status=progress conv=fsync
    ```

## Step 3: Extract the Raspberry Pi MAC Address

- If you have a Pico with screen then plug it into the Raspberry Pi USB port and power on the Pi. The MAC address will be displayed on the screen within a minute.
- Otherwise you will need to boot the Raspberry Pi and get the MAC address from the command line.
  ```bash
  ip link show eth0
  ```

## Step 4: Configure an IP Address for the Raspberry Pi

- Launch infoblox (or other DHCP management tool) and create a new DHCP reservation for the Raspberry Pi MAC address obtained in Step 3.
- At DLS the IP address should be:
    - 10.x.20.1 for pi1
    - 10.x.20.2 for pi2
    - etc.

## Step 5: Connect the Raspberry Pi to the Network and Power it On

- Connect the Raspberry Pi to the network using a wired ethernet connection.
- Power on the Raspberry Pi using the USB-C power supply.
- Wait a few minutes as the Pi will reboot twice to expand the root filesystem and set up read-only filesystem mode.

## Step 6: Verify the New Server is Visible to the usb-remote Client
On any linux machine that can route to the new Raspberry Pi server IP, run:

```bash
uvx usb-remote config add-server <raspberry_pi_ip_address>
uvx usb-remote list
```

You should see the new server listed without errors.

## Troubleshooting

If the new server shows errors when the client tries to list devices, try the following:

```bash
ssh local@<raspberry_pi_ip_address>
# password is "local"

# check the status of the two services
sudo systemctl status usbipd
sudo systemctl status usb-remote

# check their logs for errors
journalctl -u usbipd -e
journalctl -u usb-remote -e
```


[raspiImageLink]: https://drive.google.com/file/d/10Zq5Hyd1SOx7u09zNVp8pRIa7VqsN6MS/view?usp=sharing
