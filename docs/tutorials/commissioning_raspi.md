# Commissioning a new Raspberry Pi as a usb-remote Server

## Introduction

To add remote USB device support requires a usb-remote server at the location of the USB devices. e.g. In a beamline's experimental hutch. This tutorial describes how to commission a new Raspberry Pi to act as a usb-remote server.


## Step 1: Obtain and Assemble Recommended Hardware

See [Recommended Hardware](../reference/recommended_hardware.md) for the list of recommended hardware to use for a Raspberry Pi usb-remote server.

Any Raspberry Pi 4 or 5 with at least 4GB RAM and at least 16GB microSD card is suitable.

TODO: some notes on assembly go here.

## Step 2a: Obtain Raspberry Pi usb-remote Server microSD Card

If you have a supply of pre-built Raspberry Pi usb-remote server sdcard images you can skip this step and go to `Step 3: Extract the Raspberry Pi MAC Address`.

At DLS these can be obtained from TODO: where?

## Step 2b: Flash the Raspberry Pi usb-remote Server Image

Alternatively, flash your own card.

1. Obtain the latest Raspberry Pi usb-remote server image.
    - At DLS this is available at /dls_sw/apps TODO: add path here.
    - giles' latest image can be downloaded from here: [raspi-lite-usb-remote-2.1.0.img on Google Drive][raspiImageLink]
    - Alternatively, build your own image using the instructions at [Create a New Raspberry Pi Boot Image From Scratch](../how-to/new_raspi.md).
1. Insert a microSD card of at least 16GB capacity into a card reader connected to your computer.
1. Use `lsblk` to identify the device name of the microSD card (e.g. `/dev/sdb`).
1. Flash the image to a microSD card. **CAREFUL** - replace `/dev/sdX` with the correct device name for your microSD card and remember that this will overwrite the specified device.
    ```bash
    sudo dd if=./raspi-lite-usb-remote-2.1.0.img of=/dev/sdX bs=4M status=progress conv=fsync
    ```

## Step 3: Extract the Raspberry Pi MAC Address

- TODO: this will involve booting the Pi with a printer plugged in.
- Alternatively, if you have access to a monitor and keyboard you can boot the Pi and run `ip link show eth0` to get the MAC address of the `eth0` interface.


## Step 4: Configure an IP Address for the Raspberry Pi

- TODO: infoblox instructions go here.

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


[raspiImageLink]: https://drive.google.com/file/d/1zlAM9k-y9gVM7K47EDJZKzh3DB3L_1QD/view?usp=sharing
