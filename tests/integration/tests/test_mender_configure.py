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

import json
import logging
import os
import tempfile

from mender_test_containers.helpers import run, put

from helpers import make_configuration_artifact, make_configuration_apply_script


def test_mender_configure_successful_deployment(
    setup_test_container, setup_tester_ssh_connection
):
    # Install a no-op configuration apply script
    make_configuration_apply_script(setup_tester_ssh_connection, "#/bin/sh\nexit 0\n")

    # Generate a simple confiugration artifact
    configuration = {"key": "value"}
    configuration_artifact = tempfile.NamedTemporaryFile(suffix=".mender", delete=False)
    configuration_artifact_name = configuration_artifact.name

    make_configuration_artifact(
        configuration, "configuration-artifact", configuration_artifact_name
    )

    # Install the configuration artifact
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

    # Verify the content of the configuration
    result = run(
        setup_tester_ssh_connection,
        "cat /var/lib/mender-configure/device-config.json",
        warn=True,
    )
    logging.debug(result)

    assert "key" in result.stdout, result
    assert "value" in result.stdout, result

    device_config = json.loads(result.stdout)
    assert device_config == configuration


def test_mender_configure_successful_deployment_needs_reboot(
    setup_test_container, setup_tester_ssh_connection
):
    # Install a configuration apply script which requires reboot
    make_configuration_apply_script(setup_tester_ssh_connection, "#/bin/sh\nexit 20\n")

    # Generate a simple confiugration artifact
    configuration = {"key": "value"}
    configuration_artifact = tempfile.NamedTemporaryFile(suffix=".mender", delete=False)
    configuration_artifact_name = configuration_artifact.name

    make_configuration_artifact(
        configuration, "configuration-artifact", configuration_artifact_name
    )

    # Install the configuration artifact
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
        assert (
            "At least one payload requested a reboot of the device it updated."
            in result.stdout
        )
    finally:
        os.unlink(configuration_artifact_name)

    # Verify the content of the configuration
    result = run(
        setup_tester_ssh_connection,
        "cat /var/lib/mender-configure/device-config.json",
        warn=True,
    )
    logging.debug(result)
    assert result.exited == 0

    assert "key" in result.stdout, result
    assert "value" in result.stdout, result

    device_config = json.loads(result.stdout)
    assert device_config == configuration

    # Verify the needs-reboot file
    result = run(
        setup_tester_ssh_connection,
        "ls /data/mender/modules/v3/payloads/0000/tree/needs-reboot",
        warn=True,
    )
    logging.debug(result)
    assert result.exited == 0


def test_mender_configure_failed_deployment_config_is_a_folder(
    setup_test_container, setup_tester_ssh_connection
):
    # Install a configuration apply script which requires reboot
    make_configuration_apply_script(setup_tester_ssh_connection, "#/bin/sh\nexit 0\n")

    # Lock the configuration file with a folder
    run(
        setup_tester_ssh_connection,
        "mkdir -p /var/lib/mender-configure/device-config.json",
        warn=True,
    )

    # Generate a simple confiugration artifact
    new_configuration = {"new-key": "new-value"}
    configuration_artifact = tempfile.NamedTemporaryFile(suffix=".mender", delete=False)
    configuration_artifact_name = configuration_artifact.name

    make_configuration_artifact(
        new_configuration, "configuration-artifact", configuration_artifact_name
    )

    # Install the configuration artifact
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
        assert result.exited != 0
        assert (
            "Installation failed: Update module terminated abnormally: exit status 1"
            in result.stderr
        )
    finally:
        os.unlink(configuration_artifact_name)


def test_mender_configure_failed_deployment_apply_fails(
    setup_test_container, setup_tester_ssh_connection
):
    # Install a configuration apply script which requires reboot
    make_configuration_apply_script(setup_tester_ssh_connection, "#/bin/sh\nexit 2\n")

    # Install a pre-existing configuration
    configuration = {"key": "value"}
    configuration_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    configuration_file_name = configuration_file.name
    open(configuration_file_name, "w").write(json.dumps(configuration))
    put(
        setup_tester_ssh_connection,
        configuration_file_name,
        key_filename=setup_test_container.key_filename,
        remote_path="/var/lib/mender-configure/device-config.json",
    )
    os.unlink(configuration_file_name)

    # Generate a simple confiugration artifact
    new_configuration = {"new-key": "new-value"}
    configuration_artifact = tempfile.NamedTemporaryFile(suffix=".mender", delete=False)
    configuration_artifact_name = configuration_artifact.name

    make_configuration_artifact(
        new_configuration, "configuration-artifact", configuration_artifact_name
    )

    # Install the configuration artifact
    try:
        put(
            setup_tester_ssh_connection,
            configuration_artifact_name,
            key_filename=setup_test_container.key_filename,
            remote_path="/data/configuration-artifact.mender",
        )

        # Disable writes to the file
        run(
            setup_tester_ssh_connection,
            "chattr -i /var/lib/mender-configure/device-config.json",
            warn=True,
        )

        result = run(
            setup_tester_ssh_connection,
            "mender -install /data/configuration-artifact.mender",
            warn=True,
        )
        logging.debug(result)
        assert result.exited != 0
        assert (
            "Installation failed: Update module terminated abnormally: exit status 2"
            in result.stderr
        )
    finally:
        os.unlink(configuration_artifact_name)

    # Verify the content of the configuration
    result = run(
        setup_tester_ssh_connection,
        "cat /var/lib/mender-configure/device-config.json",
        warn=True,
    )
    logging.debug(result)
    assert result.exited == 0

    assert "key" in result.stdout, result
    assert "value" in result.stdout, result

    device_config = json.loads(result.stdout)
    assert device_config == configuration
