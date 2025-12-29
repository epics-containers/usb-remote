# Updating an Existing Raspberry Pi Boot Image

To upgrade the version of usb-remote or other software on an existing Raspberry Pi image, you can follow these steps.

1. Boot up a Raspberry Pi using the existing microSD card image. Make sure you have network connectivity so you can ssh into the Pi.

1. SSH into the Raspberry Pi. The default username is `local` and the default password is `local`.
   ```bash
   ssh local@<raspberry_pi_ip_address>
   ```

1. restore the root file system to writeable mode:
   ```bash
   sudo raspi-config nonint do_expand_rootfs 1
   # on reboot the root fs will be writeable
   sudo reboot
   ```

1. Update the (root) version of usb-remote:
   ```bash
   sudo -s # uv (installed by root) requires the root profile so use sudo -s
   uv tool install usb-remote==2.2.2 --upgrade
   ```

1. Make any other desired changes. e.g. delete the local user and add your own user/password.

1. Restore `runonce.sh` to re-enable read-only filesystem mode on next boot:
   ```bash
   cp /var/local/runonce.sh.done /var/local/runonce.sh
   ```

1. Create a new img file using these instructions: {ref}`create-a-backup-image`.
