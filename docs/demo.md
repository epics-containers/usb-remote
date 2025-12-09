# Demo steps

Specific to giles laptop and two pis (pi1 and pi2)

## Setup

- wire giles laptop to controls dev
- get UI up on pi1/pi2 and
  - run '/bin/fort' to get a VPN
  - ifconfig and write down the ip address of ppp interface (172.23.36.xx)
- plug in a usb hub to giles laptop with two microscopes and LifeCam camera
- edit ~/.config/awusb/awusb.config to have the ips of pi1 and pi2 + 172.23.242.210 (laptop)

## Demo

- cheese &
  - showing no cameras
- awusb list
  - see the devices on the 3 servers
- do attachments:
  - awusb attach --id=0c45:1a90 --bus=1-2.1
  - awusb attach --id=0c45:1a90 --bus=1-2.2
  - awusb attach --desc LifeCam
- cheese &
  - now see 3 cameras in cheese
- plug keyboard into pi1
- awusb list
  - see keyboard attached to pi1
- awusb attach --desc Wired
  - demo typing
- plug keyboard into p2
- awusb attach --desc Wired
  - demo typing
- clean up
  - awusb detach --id=0c45:1a90 --bus=1-2.1
  - awusb detach --id=0c45:1a90 --bus=1-2.2
  - awusb detach --desc LifeCam
  - awusb detach --desc Wired
