#!/usr/bin/env python3
"""Manual system test for client-service.

This script sends attach or detach commands to a running client-service
with flexible device search criteria.

Usage:
    uv run python test_client_service_manual.py [options]

Examples:
    # Attach first webcam
    uv run python test_client_service_manual.py --desc Webcam --first

    # Detach specific device by ID
    uv run python test_client_service_manual.py --detach --id 0bda:5400

    # Attach by serial number from specific host
    uv run python test_client_service_manual.py --serial ABC123 --host 192.168.1.100
"""

import argparse
import json
import socket
import sys

# Configuration
CLIENT_SOCKET_PATH_USER = "/tmp/usb-remote-client.sock"
CLIENT_SOCKET_PATH_SYSTEM = "/run/usb-remote-client/usb-remote-client.sock"


def send_device_request(
    command="attach",
    id=None,
    bus=None,
    serial=None,
    desc=None,
    first=False,
    host=None,
    socket_path=CLIENT_SOCKET_PATH_SYSTEM,
):
    """
    Send an attach or detach request to the client-service.

    Args:
        command: "attach" or "detach"
        id: Device ID (e.g., "0bda:5400")
        bus: Device bus ID (e.g., "1-2.3.4")
        serial: Device serial number
        desc: Device description to search for
        first: Whether to attach/detach the first match
        host: Optional server host (None = use configured servers)
        socket_path: Path to Unix socket (default: system socket)

    Returns:
        Response dictionary
    """
    request = {"command": command, "first": first}

    # Only include search criteria if provided
    if id is not None:
        request["id"] = id
    if bus is not None:
        request["bus"] = bus
    if serial is not None:
        request["serial"] = serial
    if desc is not None:
        request["desc"] = desc
    if host is not None:
        request["host"] = host

    print(f"\nSending {command} request to {socket_path}:")
    print(json.dumps(request, indent=2))

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(10.0)
            sock.connect(socket_path)
            sock.sendall(json.dumps(request).encode("utf-8"))

            response_data = sock.recv(4096).decode("utf-8")
            print("\nReceived response:")
            response = json.loads(response_data)
            print(json.dumps(response, indent=2))
            return response

    except TimeoutError:
        print("ERROR: Connection timed out", file=sys.stderr)
        return None
    except ConnectionRefusedError:
        print("ERROR: Connection refused - is client-service running?", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def main():
    """Run the manual test."""
    parser = argparse.ArgumentParser(
        description="Manual system test for client-service"
    )
    parser.add_argument(
        "--detach",
        action="store_true",
        help="Send detach command instead of attach",
    )
    parser.add_argument("--id", "-d", help="Device ID e.g. 0bda:5400", metavar="ID")
    parser.add_argument("--serial", "-s", help="Device serial number", metavar="SERIAL")
    parser.add_argument("--desc", help="Device description substring", metavar="DESC")
    parser.add_argument(
        "--host", "-H", help="Server hostname or IP address", metavar="HOST"
    )
    parser.add_argument("--bus", "-b", help="Device bus ID e.g. 1-2.3.4", metavar="BUS")
    parser.add_argument(
        "--first",
        "-f",
        action="store_true",
        help="Attach/detach the first match if multiple found",
    )
    parser.add_argument(
        "--user",
        action="store_true",
        help="Connect to user service socket (/tmp) instead of system socket (/run)",
    )
    args = parser.parse_args()

    command = "detach" if args.detach else "attach"
    socket_path = CLIENT_SOCKET_PATH_USER if args.user else CLIENT_SOCKET_PATH_SYSTEM

    print("=" * 60)
    print("Client-Service Manual System Test")
    print("=" * 60)

    try:
        # Send the device request
        response = send_device_request(
            command=command,
            id=args.id,
            bus=args.bus,
            serial=args.serial,
            desc=args.desc,
            first=args.first,
            host=args.host,
            socket_path=socket_path,
        )

        if response:
            if response.get("status") == "success":
                print(f"\n✅ Test PASSED - Device {command}ed successfully!")
                device = response.get("data", {})
                print("\nDevice Details:")
                print(f"  Bus ID: {device.get('bus_id')}")
                print(f"  Description: {device.get('description')}")
                print(f"  Serial: {device.get('serial')}")
                print(f"  Server: {response.get('server')}")
                local_devices = response.get("local_devices", [])
                if local_devices:
                    print(f"  Local devices: {', '.join(local_devices)}")
            else:
                print(f"\n⚠️  Test result: {response.get('status')}")
                print(f"Message: {response.get('message', 'N/A')}")
        else:
            print("\n❌ Test FAILED - No response received")

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")

    print("\n" + "=" * 60)
    print("Test complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
