# Success Matrix for Podman

My current succes matrix in podman looks like:
The client matrix is as follows:

| Machine | succeeds | podman?            | Tunneled | OS           |
| ------- | -------- | ------------------ | -------- | ------------ |
| ws03    | YES      | host CLI + service | yes      | Ubuntu 24.10 |
| ws03    | NO       | 5.4.2              | yes      | Ubuntu 24.10 |
| pc0116  | YES      | 5.6.0              | yes      | RHEL9        |
| b01-1   | NO       | 4.9.4              | no       | RHEL8        |

failure looks like:
```plaintext
2025-12-04 12:51:34 INFO  :Device 1101 UNBOUND from connection 1 (success 1)
2025-12-04 12:51:36 INFO  :Device 1101 BOUND to connection 1 speed 0 (success 1)
2025-12-04 12:51:36 ERROR :Open error 13 while attaching device to the virtual host controller
2025-12-04 12:51:36 ERROR :Error attaching remote device 1101 to vhci_hcd virtual port 0
```

success looks like:
```plaintext
2025-12-04 13:08:06 INFO  :Logging to /tmp/log
2025-12-04 13:08:06 INFO  :AnywhereUSB Manager 3.1.38.1 starting (Compiled: Sep 18 2025 14:21:24)
2025-12-04 13:08:06 INFO  :Client OS is Linux 5.14.0-611.8.1.el9_7.x86_64 x86_64
2025-12-04 13:08:06 INFO  :Using config at /root/.AnywhereUSB/awusb.ini
2025-12-04 13:08:06 INFO  :AnywhereUSB Manager is running headless
2025-12-04 13:08:06 INFO  :Auto-find (Bonjour SSL) on
2025-12-04 13:08:07 INFO  :Using client cert /root/.AnywhereUSB/awusb_client_cert.pem
2025-12-04 13:08:08 INFO  :127.0.0.1:18574 connected as connection 1 (secure)
2025-12-04 13:08:08 INFO  :Activated only 8 virtual USB devices!
2025-12-04 13:08:08 INFO  :Device 1101 BOUND to connection 1 speed 0 (success 1)
```
