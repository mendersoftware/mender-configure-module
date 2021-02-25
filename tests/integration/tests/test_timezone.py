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

import re
import tempfile

from mender_test_containers.helpers import run, put


def test_timezone_script(setup_test_container, setup_tester_ssh_connection):
    run(setup_tester_ssh_connection, "mount / -o remount,rw")

    try:
        run(
            setup_tester_ssh_connection,
            "mkdir -p /usr/lib/mender-configure/apply-device-config.d",
        )
        put(
            setup_tester_ssh_connection,
            "../../scripts/timezone",
            key_filename=setup_test_container.key_filename,
            remote_path="/usr/lib/mender-configure/apply-device-config.d/timezone",
        )
        run(setup_tester_ssh_connection, "mkdir -p /data/mender-configure")

        def set_timezone(timezone):
            with tempfile.NamedTemporaryFile() as fd:
                fd.write(("""{"timezone":"%s"}""" % timezone).encode())
                fd.flush()
                put(
                    setup_tester_ssh_connection,
                    fd.name,
                    key_filename=setup_test_container.key_filename,
                    remote_path="/data/mender-configure/device-config.json",
                )
            run(
                setup_tester_ssh_connection,
                "/usr/lib/mender-configure/apply-device-config.d/timezone /data/mender-configure/device-config.json",
            )

        set_timezone("UTC")
        res = run(setup_tester_ssh_connection, "timedatectl status")
        assert re.search("Time zone: *UTC", res.stdout) is not None

        old_hour = run(setup_tester_ssh_connection, "date +%H").stdout.strip()

        set_timezone("Asia/Tokyo")
        res = run(setup_tester_ssh_connection, "timedatectl status")
        assert re.search("Time zone: *Asia/Tokyo", res.stdout) is not None

        new_hour = run(setup_tester_ssh_connection, "date +%H").stdout.strip()
        assert abs(int(new_hour) - int(old_hour)) > 5

    finally:
        run(setup_tester_ssh_connection, "timedatectl set-timezone UTC")
        run(setup_tester_ssh_connection, "mount / -o remount,ro")
