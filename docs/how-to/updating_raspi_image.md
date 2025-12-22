# Updating an Existing Raspberry Pi Boot Image

To upgrade the version of usb-remote or other software on an existing Raspberry Pi boot image, you can follow these steps.

1. Boot up a Raspberry Pi using the existing microSD card image. Make sure you have network connectivity so you can ssh into the Pi.
2. SSH into the Raspberry Pi. The default username is `local` and the default password is `local`.
   ```bash
   ssh local@<raspberry_pi_ip_address>
   ```
3. restore the root file system to writeable mode:
   ```bash
   sudo mount -o remount,rw /
   ```
4. Update the (root) version of usb-remote:
   ```bash
   sudo /home/local/.local/bin/uv tool install usb-remote==2.1.0 --upgrade
   ```

TODO complete this page.
