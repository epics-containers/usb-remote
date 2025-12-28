#!/usr/bin/env python3
"""Manual system test for client-service.

This script sends attach or detach commands to a running client-service
with desc="Webcam" and first=true.

Usage:
    uv run python test_client_service_manual.py [--detach]
"""

import argparse
import json
import socket
import sys

# Configuration
CLIENT_HOST = "127.0.0.1"
CLIENT_PORT = 5056


def send_device_request(command="attach", desc="Webcam", first=True, host=None):
    """
    Send an attach or detach request to the client-service.

    Args:
        command: "attach" or "detach"
        desc: Device description to search for
        first: Whether to attach/detach the first match
        host: Optional server host (None = use configured servers)

    Returns:
        Response dictionary
    """
    request = {
        "command": command,
        "desc": desc,
        "first": first,
    }
    if host:
        request["host"] = host

    print(f"\nSending {command} request:")
    print(json.dumps(request, indent=2))

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(10.0)
            sock.connect((CLIENT_HOST, CLIENT_PORT))
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
    args = parser.parse_args()

    command = "detach" if args.detach else "attach"

    print("=" * 60)
    print("Client-Service Manual System Test")
    print("=" * 60)

    try:
        # Send the device request
        response = send_device_request(command=command, desc="Webcam", first=True)

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
