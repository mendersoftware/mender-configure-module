#!/usr/bin/env python3
# Copyright 2021 Northern.tech AS
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
#

import os

from ext4_manipulator import get, put, extract_ext4, insert_ext4


def main():
    img = "mender-image-full-cmdline-rofs-qemux86-64.uefiimg"

    # Extract ext4 image from img.
    rootfs = "%s.ext4" % img
    extract_ext4(img=img, rootfs=rootfs)

    # Install module
    put(
        local_path="mender-configure",
        remote_path="/usr/share/mender/modules/v3/mender-configure",
        rootfs=rootfs,
        remote_path_mkdir_p=True,
    )

    # Install inventory script
    put(
        local_path="mender-inventory-mender-configure",
        remote_path="/usr/share/mender/inventory/mender-inventory-mender-configure",
        rootfs=rootfs,
        remote_path_mkdir_p=True,
    )

    # Put back ext4 image into img.
    insert_ext4(img=img, rootfs=rootfs)


if __name__ == "__main__":
    main()
