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

import logging
import os
import tempfile

from mender_test_containers.helpers import run, put

from helpers import make_configuration_artifact


def test_mender_configure(setup_test_container, setup_tester_ssh_connection):
    configuration = {"key": "value"}
    configuration_artifact = tempfile.NamedTemporaryFile(suffix=".mender", delete=False)
    configuration_artifact_name = configuration_artifact.name

    # Install the apply-device-config script
    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.write("#/bin/sh\nexit 0\n".encode("utf-8"))
    tf.close()

    try:
        run(
            setup_tester_ssh_connection, "mount -o remount,rw /", warn=True,
        )
        run(
            setup_tester_ssh_connection,
            "mkdir -p /usr/lib/mender-configure",
            warn=True,
        )
        put(
            setup_tester_ssh_connection,
            configuration_artifact_name,
            key_filename=tf.name,
            remote_path="/usr/lib/mender-configure/apply-device-config",
        )
        run(
            setup_tester_ssh_connection,
            "chmod 755 /usr/lib/mender-configure/apply-device-config",
            warn=True,
        )
    finally:
        os.unlink(tf.name)

    # Install the configuration artifact
    make_configuration_artifact(
        configuration, "configuration-artifact", configuration_artifact_name
    )
    try:
        put(
            setup_tester_ssh_connection,
            configuration_artifact_name,
            key_filename=setup_test_container.key_filename,
            remote_path="/data/configuration-artifact.mender",
        )

        result = run(
            setup_tester_ssh_connection,
            "mender -install /data/configuration-artifact.mender",
            warn=True,
        )
        logging.debug(result)
        assert result.exited == 0
    finally:
        os.unlink(configuration_artifact_name)
