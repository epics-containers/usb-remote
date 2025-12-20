# Create a New Raspberry Pi Boot Image From Scratch

## Introduction

IMPORTANT: normal operation for setting up a new Raspberry Pi is to use the provided pre-built image sdcards. See [Commissioning a new Raspberry Pi Server](../tutorials/commissioning_raspi.md).

This page is only useful if you need to create a completely new sdcard with a new image, perhaps because a new version of Raspberry Pi OS has been released.

If you just want to update an existing image, e.g. to update the version of usb-remote it uses see [Updating an Existing Raspberry Pi Boot Image](updating_raspi_image.md).

## Prerequisites

You will need:

- A computer running Linux on which you have full sudo privileges.
- A microSD card of at least 16GB capacity.
- A microSD card reader connected to your computer.
- A Raspberry Pi 4 or 5 to run the image on see [Recommend Hardware](../reference/recommended_hardware.md).

## Step 1 Image the microSD Card with Raspberry Pi OS

1. Download the latest Raspberry Pi OS Lite image from the [Raspberry Pi website](https://www.raspberrypi.com/software/operating-systems/).
    - If you plan to use the Raspberry Pi's GUI capabilities, use "Raspberry Pi OS Full" version. Use full if you want to connect to the GovWiFi network which requires a GUI for setup.
1. Use `lsblk` to get a list of block devices on your system before inserting the microSD card.
1. Insert the microSD card into your card reader and connect it to your computer.
1. Use `lsblk` again to identify the device name of the microSD card (e.g. `/dev/sdb`).
1. uncompress the downloaded Raspberry Pi OS image.
    ```bash
     cd ~/Downloads
     unxz ./2025-12-04-raspios-trixie-arm64.img.xz
     ```
1. Use `dd` to write the Raspberry Pi OS image to the microSD card. Replace `/dev/sdX` with the actual device name of your microSD card. Be very careful with this command as it will overwrite the specified device.
    ```bash
    sudo dd if=./2025-12-04-raspios-trixie-arm64.img of=/dev/sdX bs=4M status=progress conv=fsync
    ```

## Step 2 Configure the Raspberry Pi OS Image

1. Mount the microSD card boot partition. Replace `/dev/sdX1` with the actual device name of the boot partition of your microSD card.
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
    sudo vim /boot/cmdline.txt
    # add " ip=<your_static_ip_address>" at the end of the single line in the file.
    ```
1. Finally unmount the boot partition.
    ```bash
    cd ..
    sudo umount sdcard-bootfs
    # there may also be a second mount point:
    sudo umount /dev/sdX
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
1. Take this opportunity to write down the Raspberry Pi's MAC address for future reference.
    ```bash
    ip link show eth0
    # look for "link/ether xx:xx:xx:xx:xx:xx"
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

## Step 6 image-backup

1. Clone the image-backup repository.
    ```bash
    cd ~
    git clone https://github.com/seamusdemora/RonR-RPi-image-utils.git
    ```
1. Install image-backup.
    ```bash
    sudo install --mode=755 ~/RonR-RPi-image-utils/image-* /usr/local/sbin
    ```

## Step 7 Clean Up The Settings for Production

The master sdcard image wants to use DHCP only and be isolated from the internet so we need to undo any temporary configuration changes made earlier. This allows us to re-use the image on multiple Raspberry Pis which will each get their own IP address via DHCP.

1. Disable the static IP address if you set one up.
    ```bash
    sudo apt install vim
    sudo vim /boot/firmware/cmdline.txt
    # remove " ip=<your_static_ip_address>" that you added earlier
    ```
1. Disable Wifi if you enabled it.
    ```bash
    sudo vim /boot/firmware/config.txt
    # add the following lines at the end of the file
    dtoverlay=disable-wifi
    dtoverlay=disable-bt
    ```

## Step 8 Create a Backup Image of the microSD Card

Before backing up the image we put the SD card into read-only mode. This avoids wearing out the SD card and makes the Pi reset to a clean state on each boot.

1. Set the SD card to read-only mode with an overlay filesystem in RAM.
    ```bash
    sudo raspi-config nonint enable_overlayfs
    sudo raspi-config nonint enable_bootro
    # DO NOT reboot until the backup image has been created
    # ALSO: ignore warnings about fstab has been modifiedsyn
    ```

1. Insert a USB stick into the Raspberry Pi to store the backup image.

1. use `lsblk` to identify the device name of the USB stick 1st partition (e.g. `/dev/sda1`). It should already be mounted under `/media/local/xxxx`. If there is no mount then create a mount point and mount it manually:
    ```bash
    sudo mkdir -p /media/local/usb
    sudo mount /dev/sda1 /media/local/usb
    ```

1. Run the image-backup script to create a backup image of the microSD card to the USB stick. Replace `/media/local/xxxx` with the actual mount point of your USB stick and adjust the output file path as needed.
    ```bash
    sudo image-backup
    # when promted for output file, use something like:
    /media/local/usb/raspi-usb-remote-2025.12.20.img
    # choose the defaults for the other prompts and y to confirm file creation.
    ```
1. sync and unmount the USB stick.
    ```bash
    sync
    sudo umount /media/local/xxxx
    ```
1. You can now power off the Raspberry Pi and remove the USB stick.
    ```bash
    sudo poweroff
    ```

## Conclusion

You now have a backup image of your configured Raspberry Pi microSD card that you can use to create additional Raspberry Pi servers as needed. To restore the image to another microSD card, use the `dd` command as described in Step 1, replacing the input file with your backup image file.

The Raspberry Pi you have just been working with is now ready to be used as a production server. Simply power it back on and it will boot into read-only mode with usb-remote installed and ready to use.

You should configure your router or `infoblox` to assign it a DHCP reservation so it always gets the same IP address. To do this requires knowing the Raspberry Pi's MAC address.

See [Commissioning Additional Raspberry Pi Servers](../tutorials/commissioning_raspi.md) for instructions on deploying the backup image to new Raspberry Pis.
