# Setup Rasberry Pi Pico for MAC Address Display

## Intro

This guide explains how to set up a Raspberry Pi Pico with an OLED display to show the MAC address of a Raspberry Pi when powered on. This is useful for commissioning new Raspberry Pi usb-remote servers.

In particular, if you are using this at DLS, we expect the Pi Server to be deployed into a beamline instrumentation network. You need the Mac address of the Pi to create a DHCP reservation for it in Infoblox. Having the Pico display the MAC address means that your commissioning process is:

- Put a pre-configured Raspberry Pi usb-remote server microSD card in a Raspberry Pi and power it on.
- Plug the Pico into the Raspberry Pi USB port and wait for the MAC address to be displayed.
- Use the displayed MAC address to create a DHCP reservation in Infoblox.
- Take the Raspberry Pi to the beamline, connect it to the instrumentation network and power it on.

## Code on the Pico

TODO: expand this into a full explanation.

- flash the Pico with the UF2 for MicroPython from <https://micropython.org/download/RPI_PICO/>
- save the following code as `main.py` on the Pico filesystem.


TODO: this code is for a different IC2 OLED display - need to change to the correct one for the Pico OLED 1.3"
```python
import asyncio
import select
import sys

from hardware.outputs import display

# Set up the poll object
poll_obj = select.poll()
poll_obj.register(sys.stdin, select.POLLIN)


async def main():
    display.lcd_print("Await input ... ", 0)
    await asyncio.sleep(1)

    while True:
        # Wait for input on stdin, waiting for 100 ms
        poll_results = poll_obj.poll(100)
        if poll_results:
            # Read the data from stdin (read data coming from PC)
            data = sys.stdin.readline().strip()
            # Write the data to the input file
            sys.stdout.write("received data: " + data + "\r")
            if len(data) > 0:
                display.lcd_print(data, 1)
        else:
            # do something if no message received (like feed a watchdog timer)
            continue

        await asyncio.sleep(1)


asyncio.run(main())
```
