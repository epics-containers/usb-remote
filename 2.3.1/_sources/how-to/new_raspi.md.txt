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
- A USB stick of at least 8GB capacity to store the backup image.
- Possibly a monitor and microHDMI to HDMI cable if you want to use the Pi GUI.

## Options

The sequence of events to set this up is:
- Image the microSD card with Raspberry Pi OS.
- Boot a Raspberry Pi from the microSD card and do some additional configuration.
- Take a backup image of the microSD card to use as an image for creating more sdcards.

In order to connect to the Raspberry Pi for configuration you have two options:
1. Connect a monitor and keyboard to the Raspberry Pi directly. Make sure you use the "Raspberry Pi OS" version which includes the GUI.
2. Connect via SSH to the Raspberry Pi's IP address. For this to work you need to be able to determine (or fix) the Raspberry Pi's IP address on your network.

In both cases you will need access to the internet from the Raspberry Pi to download and install packages. Your options are:
1. Make sure that your Pi is connected to your wired ethernet network which has internet access.
2. Temporarily connect to Wifi to get internet access during setup. At DLS the GovWiFi network is an easy option for this. You will need to use the GUI option above to set up the Wifi connection.

Bear in mind that the preferred production configuration for usb-remote Raspberry Pis is to have no internet access and only use wired ethernet with a DHCP assigned IP address. The temporary internet access is only needed to download and install packages during setup.


## Step 1 Image the microSD Card with Raspberry Pi OS

1. Download the latest 'Raspberry Pi OS Lite' image from the [Raspberry Pi website](https://www.raspberrypi.com/software/operating-systems/). The Lite version is the last option on the linked page.
    - If you need the Pi desktop GUI, then use 'Raspberry Pi OS' image.

1. Use `lsblk` to get a list of block devices on your system before inserting the microSD card.

1. Insert the microSD card into your card reader and connect it to your computer.

1. Use `lsblk` again to identify the device name of the microSD card (e.g. `/dev/sdb`).

1. uncompress the downloaded Raspberry Pi OS image.
    ```bash
     cd ~/Downloads
     unxz ./2025-12-04-raspios-trixie-arm64-lite.img.xz
     ```

1. Use `dd` to write the Raspberry Pi OS image to the microSD card. Replace `/dev/sdX` with the actual device name of your microSD card. Be very careful with this command as it will overwrite the specified device.
    ```bash
    sudo dd if=./2025-12-04-raspios-trixie-arm64-lite.img of=/dev/sdX bs=4M status=progress conv=fsync
    ```

## Step 2 Configure the Raspberry Pi OS Image

IMPORTANT: These steps must be done before the first boot of the Raspberry Pi. The files we set up here are only read by the Raspberry Pi during its first boot.

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

1. If you need a static IP address for wired ethernet, edit `cmdline.txt`.
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

## Step 3 First Boot and Connect to Internet

1. Insert the microSD card into your Raspberry Pi and power it on.

1. Your options for connecting to the Raspberry Pi are:
    - Connect a monitor and keyboard to the Raspberry Pi directly. This is not available if you are using the 'Lite' version and requires a microHDMI to HDMI cable and a monitor.
    - Connect via SSH to the Raspberry Pi's IP address. The username is `local` and the password is `local`. If you have access to your router then it will show the Raspberry Pi's IP address in its connected devices list. The best alternative is to set a fixed IP in the boot configuration as described above.

1. If you do not have internet access then temporarily connect to Wifi:
    - sudo raspi-config
    - Select "System Options" -> "Wireless LAN"
    - Enter your SSID and password
    - Finish
    - ping google.com to check internet access (try `sudo reboot` if it does not work immediately)
    If you need to connect to GovWiFi then you require the GUI version of the OS see [Connecting to GovWiFi](../reference/govwifi_setup.md).

1. Once connected, update the package lists and upgrade installed packages, plus get vim and git.
    ```bash
    sudo apt update
    sudo apt upgrade -y
    sudo apt install -y git vim
    ```
1. Take this opportunity to write down the Raspberry Pi's MAC address for future reference.
    ```bash
    ip link show eth0
    # look for "link/ether xx:xx:xx:xx:xx:xx"
    ```

## Step 4 Install and Configure usbip

1. Add the kernel modules to `/etc/modules-load.d` so they load at boot.
    ```bash
    sudo modprobe usbip_core
    sudo modprobe usbip_host
    echo -e "usbip-core\nusbip-host" | sudo tee /etc/modules-load.d/usbip.conf
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
    curl -LsSfO https://astral.sh/uv/install.sh
    sudo bash install.sh
    ```

1. Install `usb-remote` system service.
    ```bash
    sudo -s # uv (installed by root) requires the root profile so use sudo -s
    uvx usb-remote install-service server
    systemctl enable --now usb-remote
    systemctl status usb-remote # check it is running correctly
    exit
    ```

## Step 6 image-backup

`image-backup` is a utility to create backup images of Raspberry Pi sdcards. It does clever stuff like minimizing the size of the image and expanding the filesystem on first boot of copies of the image. See <https://forums.raspberrypi.com/viewtopic.php?t=332000> for more details.

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

## Step 8 Prepare the Backup Image for Distribution

Add a `run-once service` to the image so that when copies of the image are first booted they will enable read-only mode (after the root filesystem has been expanded - this feature is added automatically by image-backup).

Read-only mode uses overlayfs in RAM to avoid wearing out the sdcard and makes the Pi reset to a clean state on each boot.

1. Set up a run once service for first boot of copies of the image.
    ```bash
    echo '[Unit]
    Description=Run script once on next boot
    ConditionPathExists=/var/local/runonce.sh
    After=multi-user.target

    [Service]
    Type=oneshot
    ExecStart=/bin/bash /var/local/runonce.sh

    [Install]
    WantedBy=multi-user.target
    ' | sudo tee /etc/systemd/system/runonce.service
    sudo systemctl enable runonce.service
    ```

1. Create the `runonce.sh` script to expand the root filesystem and enable read-only mode.
    ```bash
    echo '#!/bin/bash
    set -x

    # Disable this script from running again
    mv /var/local/runonce.sh /var/local/runonce.sh.done

    # disable services that will report errors when in RO mode
    systemctl mask dphys-swapfile.service
    systemctl mask systemd-zram-setup@zram0.service

    # enable read only overlay mode
    raspi-config nonint do_overlayfs 0

    # reboot to pick up the change
    sync; reboot
    ' | sudo tee /var/local/runonce.sh

    # Add packages required for read-only mode
    sudo apt-get -y install cryptsetup cryptsetup-bin overlayroot
    ```

## Step 9 Add a Service to Send the MAC Address to a Pico (optional)

Adding this service will monitor USB ports for a Raspberry Pi Pico being plugged in. When a Pico is detected it will send the Pi's MAC address to the Pico.

This is useful for commissioning new usb-remote servers using a Pico as described in [Setup Raspberry Pi Pico for MAC Address Display](setup_pico.md).

```bash
echo '[Unit]
Description=Monitor USB and send MAC address to any pico detected
After=multi-user.target

[Service]
ExecStart=/root/.local/bin/uvx --from usb-remote pico-send-mac

[Install]
WantedBy=multi-user.target
' | sudo tee /etc/systemd/system/send-mac.service

sudo systemctl enable send-mac --now
```

(create-a-backup-image)=
## Step 10 Create a Backup Image of the microSD Card

Before backing up the image we put the SD card into read-only mode. This avoids wearing out the SD card and makes the Pi reset to a clean state on each boot.

1. Insert a USB stick into the Raspberry Pi to store the backup image.

1. use `lsblk` to identify the device name of the USB stick 1st partition which will normally be `/dev/sda1`. Mount the USB stick at `/media/local/usb`:
    ```bash
    sudo mkdir -p /media/local/usb
    sudo mount /dev/sda1 /media/local/usb
    ```

1. Run the image-backup script to create a backup image of the microSD card to the USB stick. Replace the output file name with something appropriate including the version of usb-remote.
    ```bash
    sudo image-backup
    # when promted for output file, use something like:
    /media/local/usb/raspi-lite-usb-remote-2.2.2.img
    # choose the defaults for the other prompts and y to confirm file creation.
    ```

1. sync and unmount the USB stick.
    ```bash
    sync
    sudo umount /media/local/usb
    ```

1. You can now remove the USB stick.


That's it. Your img file can now be used to create additional Raspberry Pi usb-remote servers as needed.

To find out how to commission additional Raspberry Pi servers from this image see [Commissioning Additional Raspberry Pi Servers](../tutorials/commissioning_raspi.md).


## Conclusion

You now have a backup image of your configured Raspberry Pi microSD card that you can use to create additional Raspberry Pi servers as needed.

See [Commissioning Additional Raspberry Pi Servers](../tutorials/commissioning_raspi.md) for instructions on deploying the backup image to new Raspberry Pis.
