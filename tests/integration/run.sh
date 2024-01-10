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

# Generate docker-compose.testing.yml like integration's run.sh
cat mender_integration/docker-compose.demo.yml > mender_integration/docker-compose.testing.yml

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
python3 -m pytest ${GENERATE_PYTEST_REPORT:+--junitxml=report.xml} -v tests/ "$@"
