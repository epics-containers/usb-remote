#!/usr/bin/env python3
"""Manual system test for client-service.

This script starts the client-service and sends an attach command
with desc="Webcam" and first=true.

Usage:
    uv run python test_client_service_manual.py
"""

import json
import socket
import sys

# Configuration
CLIENT_HOST = "127.0.0.1"
CLIENT_PORT = 5056


def send_attach_request(desc="Webcam", first=True, host=None):
    """
    Send an attach request to the client-service.

    Args:
        desc: Device description to search for
        first: Whether to attach the first match
        host: Optional server host (None = use configured servers)

    Returns:
        Response dictionary
    """
    request = {
        "command": "attach",
        "desc": desc,
        "first": first,
    }
    if host:
        request["host"] = host

    print("\nSending attach request:")
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
    print("=" * 60)
    print("Client-Service Manual System Test")
    print("=" * 60)

    try:
        # Send the attach request
        response = send_attach_request(desc="Webcam", first=True)

        if response:
            if response.get("status") == "success":
                print("\n✅ Test PASSED - Device attached successfully!")
                device = response.get("data", {})
                print(
                    f"\nDevice Details:"
                    f"  Bus ID: {device.get('bus_id')}"
                    f"  Description: {device.get('description')}"
                    f"  Serial: {device.get('serial')}"
                    f"  Server: {response.get('server')}"
                )
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
