#!/bin/bash
# Copyright 2022 Northern.tech AS
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

set -x -e

MENDER_CONFIGURE=${MENDER_CONFIGURE:-../../src/mender-configure}
MENDER_INVENTORY_MENDER_CONFIGURE=${MENDER_INVENTORY_MENDER_CONFIGURE:-../../src/mender-inventory-mender-configure}
MENDER_VERSION=${MENDER_VERSION:-mender-master}

# Clean up ghost containers and volumes from previous runs. One compose project per backend
# flavour, so wipe each of them; keep this list in sync with SERVER_PROJECTS in tests/server.py.
for project in mender mender_enterprise; do
    docker compose -p "$project" -f mender_server/docker-compose.yml down -v --remove-orphans 2>/dev/null || true
    docker rm -f $(docker ps -a -q -f "name=^${project}-") 2>/dev/null || true
    docker volume rm $(docker volume ls -q -f "name=^${project}_") 2>/dev/null || true
done
docker rm -f $(docker ps -a -q -f name=virtual_device) 2>/dev/null || true

# Generate the compose files the backend fixtures use, inside the mender_server directory so that
# the relative paths in them still resolve. Same stack, minus the published host ports, so that the
# backend does not collide with anything else listening on the host.
sed -e '/9000:9000/d' -e '/8080:8080/d' -e '/443:443/d' -e '/80:80/d' -e '/ports:/d' \
    mender_server/docker-compose.yml > mender_server/docker-compose.testing.yml

sed -e '/9000:9000/d' -e '/8080:8080/d' -e '/443:443/d' -e '/80:80/d' -e '/ports:/d' \
    mender_server/compose/docker-compose.enterprise.yml > mender_server/docker-compose.testing.enterprise.yml

# Prepare Docker image
rm -f mender-image-full-cmdline-rofs-qemux86-64.uefiimg*
cp $MENDER_CONFIGURE mender-configure
cp $MENDER_INVENTORY_MENDER_CONFIGURE mender-inventory-mender-configure

docker build \
       --build-arg MENDER_CONFIGURE_LOCATION=mender-configure \
       --build-arg MENDER_INVENTORY_MENDER_CONFIGURE_LOCATION=mender-inventory-mender-configure \
       --build-arg MENDER_VERSION=$MENDER_VERSION \
       -t mendersoftware/mender-client-qemu-rofs-mender-configure .

# Extract filesystem to use in testing
docker run --rm --entrypoint cp -v $PWD:/output \
    mendersoftware/mender-client-qemu-rofs-mender-configure \
    /mender-image-full-cmdline-rofs-qemux86-64.uefiimg.ext4 \
    /output

# Run tests
python3 -m pytest ${GENERATE_PYTEST_REPORT:+--junitxml=report.xml} --verbose --verbose tests/ "$@"
