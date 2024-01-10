ARG MENDER_VERSION=mender-master
FROM mendersoftware/mender-client-qemu-rofs:${MENDER_VERSION}

ARG MENDER_CONFIGURE_LOCATION=mender-configure
ADD ${MENDER_CONFIGURE_LOCATION} /

ARG MENDER_INVENTORY_MENDER_CONFIGURE_LOCATION=mender-inventory-mender-configure
ADD ${MENDER_INVENTORY_MENDER_CONFIGURE_LOCATION} /

ADD install-mender-configure.py /
RUN /install-mender-configure.py

ENTRYPOINT source /env.txt && ./mender-qemu
