# Create a New Raspberry Pi Boot Image From Scratch

## Introduction

IMPORTANT: normal operation for setting up a new Raspberry Pi is to use the provided pre-built image sdcards. See [Commissioning a new Raspberry Pi Server](../tutorials/commissioning_raspi.md).

This page is only useful if you need to create a completely new image, perhaps because a new version of Raspberry Pi OS has been released.

If you just want to update an existing image, e.g. to update the version of usb-remote it uses see [Updating an Existing Raspberry Pi Boot Image](updating_raspi_image.md).

## Prerequisites

You will need:

- A computer running Linux on which you have full sudo privileges.
- A microSD card of at least 16GB capacity.
- A microSD card reader connected to your computer.
- A Raspberry Pi 4 or 5 to run the image on see [Recommend Hardware](../reference/recommended_hardware.md).

## Step 1 Image the microSD Card with Raspberry Pi OS

1. Download the latest Raspberry Pi OS Full image from the [Raspberry Pi website](https://www.raspberrypi.com/software/operating-systems/).
    - Note you only need full version if you plan to use the Raspberry Pi's GUI capabilities. Otherwise the "Raspberry Pi OS Lite" version is sufficient. Use full if you want to connect to the Government WiFi network which requires a GUI for setup.
1. Use `lsblk` to get a list of block devices on your system before inserting the microSD card.
1. Insert the microSD card into your card reader and connect it to your computer.
1. Use `lsblk` again to identify the device name of the microSD card (e.g. `/dev/sdX`).
1. uncompress the downloaded Raspberry Pi OS image.
    ```bash
     cd ~/Downloads
     unxz ./2025-12-04-raspios-trixie-arm64-full.img.xz
     ```
1. Use `dd` to write the Raspberry Pi OS image to the microSD card. Replace `/dev/sdX` with the actual device name of your microSD card.
    ```bash
    sudo dd if=./2025-12-04-raspios-trixie-arm64-full.img of=/dev/sdX bs=4M status=progress conv=fsync
    ```
1. Once the `dd` command has completed, run `sync` to ensure all data has been written to the microSD card.
    ```bash
    sync
    ```

## Step 2 Configure the Raspberry Pi OS Image

1. Mount the microSD card boot partition.
    ```bash
    mkdir sdcard-bootfs
    sudo mount /dev/sdX1 sdcard-bootfs
    cd sdcard-bootfs
    ```
1. Enable SSH by creating an empty file named `ssh` in the boot partition.
    ```bash
    sudo touch ssh
    ```
1. Create a user `local` with password `local` by adding a file named `userconf` in the boot partition.
    ```bash
    echo "local:$(echo local | openssl passwd -6 -stdin)" | sudo tee userconf.txt
    ```
1. If you need a static IP address for wired ethernet, edit `firmware/cmdline.txt`.
    ```bash
    sudo vim firmware/cmdline.txt
    # or sudo vim cmdline.txt if `firmware` directory does not exist
    # add <space>ip=<your_static_ip_address> at the end of the single line in the file, replacing with your desired static IP address
    ```
1. Finally unmount the boot partition.
    ```bash
    cd ..
    sudo umount sdcard-bootfs
    rmdir sdcard-bootfs
    ```
1. NOTE: the static IP configuration above must be undone before making a production image to be used on multiple Raspberry Pis. Instead we want the image to use DHCP only and be isolated from the internet.

## Step 3 First Boot and Connect to Internet

1. Insert the microSD card into your Raspberry Pi and power it on.
1. Your options for connecting to the Raspberry Pi are:
    - Connect a monitor and keyboard to the Raspberry Pi directly.
    - Connect via SSH to the Raspberry Pi's IP address. The username is `local` and the password is `local`. If you have access to your router then it will show the Raspberry Pi's IP address in its connected devices list. The best alternative is to set a fixed IP in the boot configuration as described above.
1. If you do not have internet access then temporarily connect to Wifi:
    - sudo raspi-config
    - Select "System Options" -> "Wireless LAN"
    - Enter your SSID and password
    - Finish
    - ping google.com to check internet access (try `sudo reboot` if it does not work immediately)
1. Once connected, update the package lists and upgrade installed packages.
    ```bash
    sudo apt update
    sudo apt upgrade -y
    ```

## Step 4 Install and Configure usbip
1. Add the kernel modules to `/etc/modules` so they load at boot.
    ```bash
    echo "usbip_core
    usbip_host" | sudo tee -a /etc/modules
    sudo modprobe usbip_core
    sudo modprobe usbip_host
    ```
1. Install the `usbip` package.
    ```bash
    sudo apt install -y usbip
    ```
1. Create a service to run uspipd at boot.
    ```bash
    echo "[Unit]
    Description=USB/IP Daemon
    After=network.target

    [Service]
    Type=forking
    ExecStart=/usr/sbin/usbipd -D
    Restart=on-failure

    [Install]
    WantedBy=multi-user.target" | sudo tee /etc/systemd/system/usbipd.service

    sudo systemctl enable --now usbipd.service
    sudo systemctl status usbipd.service
    ```

## Step 5 Install usb-remote

1. Install `uv`.
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    cd; source .bashrc
    ```
1. Install `usb-remote` system service.
    ```bash
    sudo .local/bin/uvx usb-remote install-service --system
    sudo systemctl enable --now usb-remote
    sudo systemctl status usb-remote
    ```
