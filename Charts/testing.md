# Testing in Cluster

Here is the theory of what needs to be done to test anyWhereUSB in cluster.

## Steps
- use the deployment.yaml [here](deployment.yaml)
- but make it privileged: true
  - for podman that means all devices are available - hopefully that applies in k8s too?
- it is possible that it will need to run as user id 1000 (for group membership). But for podman, being root in the container seems to work fine.
- perform the following steps to test against the awusb hub in b01

```bash
awusbmanager-headless -l /tmp/log
awusbmanager-headless set clientid,new_unused_name
# OK
awusbmanager-headless known hub add,127.0.0.1
# OK
awusbmanager-headless list
```

you should see:
```plaintext
 AnywhereUSB Manager version 3.1.38.1 Client ID: new_unused_name
Below are the available devices:

 AW02-050314 (127.0.0.1:18574)
    Group 1 (AW02-050314.1)
        Dell KB216 Wired Keyboard (AW02-050314.1101)
    Group 2 (AW02-050314.2)

* means Autoconnect enabled, + means Autoconnect inherited
Autofind: enabled   Use All Hub Addresses: disabled
Autoconnect All: disabled
```

then run:
```bash
awusbmanager-headless autoconnect group,AW02-050314.1
# OK
awusbmanager-headless list
```

## Expected Result

you should see:
```plaintext
 AnywhereUSB Manager version 3.1.38.1 Client ID: new_unused_name
Below are the available devices:

 AW02-050314 (127.0.0.1:18574)
*   Group 1 (AW02-050314.1) (In-use by you)
+       Dell KB216 Wired Keyboard (AW02-050314.1101) (In-use by you)
    Group 2 (AW02-050314.2)

* means Autoconnect enabled, + means Autoconnect inherited
Autofind: enabled   Use All Hub Addresses: disabled
Autoconnect All: disabled
```

It is important that the keyboard itself is showing as (In-use by you).
If you see the group is in use but no keyboard then something is wrong, check `/tmp/log`
