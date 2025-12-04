# The devcontainer should use the developer target and run as root with podman
# or docker with user namespaces.
FROM ghcr.io/diamondlightsource/ubuntu-devcontainer:noble AS developer

# The build stage installs the context into the venv
################################################################################
FROM developer AS build

# Change the working directory to the `app` directory
# and copy in the project
WORKDIR /app
COPY . /app
RUN chmod o+wrX .

# Tell uv sync to install python in a known location so we can copy it out later
ENV UV_PYTHON_INSTALL_DIR=/python

# Sync the project without its dev dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --no-dev

# The runtime stage copies the built venv into a runtime container
################################################################################
FROM ubuntu:noble AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    sudo \
    busybox \
    usbutils \
    && rm -rf /var/lib/apt/lists/* \
    && busybox --install -s

# awusbmanager should be installed by a not-root user with sudo privileges.
RUN echo "ubuntu ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
USER ubuntu

# Install the headless awusb manager from
# https://hub.digi.com/support/products/infrastructure-management/digi-anywhereusb-2-plus/
COPY awusbmanager-headless_1.2_amd64.deb /
RUN sudo apt-get update && sudo apt-get install -y --no-install-recommends \
    ./awusbmanager-headless_1.2_amd64.deb \
    && sudo rm -rf /var/lib/apt/lists/*

# remove sudo rights again
RUN sudo sed -i '/^ubuntu ALL=(ALL) NOPASSWD: ALL$/d' /etc/sudoers

# Copy the python installation from the build stage
COPY --from=build /python /python

# Copy the environment, but not the source code
COPY --from=build /app/.venv /app/.venv
ENV PATH=/app/.venv/bin:$PATH

# use root for local rootless containers in podman
# this should be run as uid 1000 in cluster
USER root
ENTRYPOINT ["bash"]
