# Run in a container

Pre-built containers with usb-remote and its dependencies already
installed are available on [Github Container Registry](https://ghcr.io/epics-containers/usb-remote).

## Starting the container

To pull the container from github container registry and run:

(privileged mode is required to access USB and modify devices)

```
$ docker --privileged run ghcr.io/epics-containers/usb-remote:latest --version
```

To get a released version, use a numbered release instead of `latest`.
