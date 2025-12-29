# Setting up a DHCP Server for testing usb-remote

usb-remote should run in an isolated network such as a DLS Beamline Instrumentation network. This is because it is insecure by design, and is intended for use in trusted networks only.

This may make testing difficult if you don't have access to such a network.

These instructions show how to set up a DHCP server on a spare NIC of your development machine. If your dev machine has only one NIC, you can use a USB-Ethernet adapter to add a second NIC.

## Install DHCP server software

On Debian/Ubuntu based systems, install the isc-dhcp-server package:

```bash
sudo apt-get install isc-dhcp-server
```

## Setup the spare NIC

This is easiest done in the Gnome Network Manager GUI.

Find the second NIC and edit its settings.

- Set the IPv4 Method to "Manual"
- Set the Address to 192.168.2.1

Other settings do not matter unless you want to set set up a route to the internet. Doing do does not create an isolated network, so is not recommended. (although it may be useful for commissioning - TODO: consider adding instructions for internet routing but no route to other local networks)

## Configure the DHCP server

Edit the file `/etc/dhcp/dhcpd.conf` to look as follows:

```text
subnet 192.168.2.0 netmask 255.255.255.0 {
  range 192.168.2.50 192.168.2.200;
   option routers 192.168.2.1;
#  option domain-name-servers 8.8.8.8, 8.8.4.4;
  authoritative;
}

host pi1 {
  hardware ethernet e4:5f:01:0e:3c:79;
  fixed-address 192.168.2.31;
}
host pi2 {
  hardware ethernet dc:a6:32:dd:77:85;
  fixed-address 192.168.2.32;
}
host pi3 {
  hardware ethernet dc:a6:32:66:c7:dd;
  fixed-address 192.168.2.33;
}
host pi4 {
  hardware ethernet e4:5f:01:94:43:6f;
  fixed-address 192.168.2.34;
}
```

Edit `/etc/default/isc-dhcp-server` to set the interfaces variable to the name of your spare NIC, e.g.

WARNING: you definitely DO NOT want to set this to your main NIC, or you will break your network connection and the rest of your LAN!

```text
INTERFACESv4=enxc8a362b78de1
INTERFACESv6=""
```

## Restart the DHCP server

```bash
sudo systemctl restart isc-dhcp-server
```

## Connect your usb-remote servers to the test network

You can add a single usb-remote server plugged directly into your spare NIC or multiple servers. For multiple servers you will need a network switch plugged into your spare NIC.

When you boot the remote servers they should get an IP address in the range 192.168.2.10 to 192.168.2.100 or a fixed address if you listed their MAC addresses in the DHCP server configuration above.
