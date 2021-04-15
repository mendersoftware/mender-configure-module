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
import pytest
import tempfile
import time

from mender_test_containers.helpers import run, put
from mender_integration.tests.MenderAPI import (
    authentication,
    devauth,
    get_container_manager,
)
from mender_integration.tests.MenderAPI.requests_helpers import requests_retry

from helpers import make_configuration_artifact, make_configuration_apply_script


def test_mender_configure_successful_install(
    setup_test_container, setup_tester_ssh_connection
):
    # Install a no-op configuration apply script
    make_configuration_apply_script(setup_tester_ssh_connection, "#/bin/sh\nexit 0\n")

    # Generate a simple configuration artifact
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
            "mender install /data/configuration-artifact.mender",
            warn=True,
        )
        logging.debug(result)
        assert result.exited == 0
    finally:
        os.unlink(configuration_artifact_name)

    # Verify the content of the configuration
    result = run(
        setup_tester_ssh_connection, "cat /var/lib/mender-configure/device-config.json",
    )
    logging.debug(result)

    assert "key" in result.stdout, result
    assert "value" in result.stdout, result

    device_config = json.loads(result.stdout)
    assert device_config == configuration

    # commit the installation
    result = run(setup_tester_ssh_connection, "mender commit", warn=True,)
    logging.debug(result)
    assert result.exited == 0

    # Generate a new configuration artifact
    configuration = {"new-key": "new-value"}
    configuration_artifact = tempfile.NamedTemporaryFile(suffix=".mender", delete=False)
    configuration_artifact_name = configuration_artifact.name

    make_configuration_artifact(
        configuration, "new-configuration-artifact", configuration_artifact_name
    )

    # Install the configuration artifact
    try:
        put(
            setup_tester_ssh_connection,
            configuration_artifact_name,
            key_filename=setup_test_container.key_filename,
            remote_path="/data/new-configuration-artifact.mender",
        )

        result = run(
            setup_tester_ssh_connection,
            "mender install /data/new-configuration-artifact.mender",
            warn=True,
        )
        logging.debug(result)
        assert result.exited == 0
    finally:
        os.unlink(configuration_artifact_name)

    # Verify the content of the configuration
    result = run(
        setup_tester_ssh_connection, "cat /var/lib/mender-configure/device-config.json",
    )
    logging.debug(result)

    assert "new-key" in result.stdout, result
    assert "new-value" in result.stdout, result

    device_config = json.loads(result.stdout)
    assert device_config == configuration


def test_mender_configure_successful_install_needs_reboot(
    setup_test_container, setup_tester_ssh_connection
):
    # Install a configuration apply script which requires reboot
    make_configuration_apply_script(setup_tester_ssh_connection, "#/bin/sh\nexit 20\n")

    # Generate a simple configuration artifact
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
            "mender install /data/configuration-artifact.mender",
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
        setup_tester_ssh_connection, "cat /var/lib/mender-configure/device-config.json",
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
        "ls /data/mender/modules/v3/payloads/0000/tree/tmp/needs-reboot",
        warn=True,
    )
    logging.debug(result)
    assert result.exited == 0


def test_mender_configure_failed_install_config_is_a_folder(
    setup_test_container, setup_tester_ssh_connection
):
    # Install a no-op configuration apply script
    make_configuration_apply_script(setup_tester_ssh_connection, "#/bin/sh\nexit 0\n")

    # Remove the configuration file if it exists
    run(
        setup_tester_ssh_connection,
        "rm -f /var/lib/mender-configure/device-config.json",
    )

    # Lock the configuration file with a folder
    run(
        setup_tester_ssh_connection,
        "mkdir -p /var/lib/mender-configure/device-config.json",
    )

    # capture artifact and provides
    result = run(setup_tester_ssh_connection, "mender show-artifact 2>/dev/null",)
    artifact = result.stdout
    result = run(setup_tester_ssh_connection, "mender show-provides 2>/dev/null",)
    provides = result.stdout

    # Generate a simple configuration artifact
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
            "mender install /data/configuration-artifact.mender",
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

    # capture the new artifact and provides and verify they didn't change
    result = run(setup_tester_ssh_connection, "mender show-artifact 2>/dev/null",)
    new_artifact = result.stdout
    result = run(setup_tester_ssh_connection, "mender show-provides 2>/dev/null",)
    new_provides = result.stdout
    assert (new_artifact, new_provides) == (artifact, provides)


def test_mender_configure_failed_install_apply_fails(
    setup_test_container, setup_tester_ssh_connection
):
    # Install a configuration apply script which fails in applying the new configuration
    make_configuration_apply_script(
        setup_tester_ssh_connection,
        """#/bin/sh
if grep -q new-key "$1"; then
    exit 2
fi
exit 0
""",
    )

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

    # capture artifact and provides
    result = run(setup_tester_ssh_connection, "mender show-artifact 2>/dev/null",)
    artifact = result.stdout
    result = run(setup_tester_ssh_connection, "mender show-provides 2>/dev/null",)
    provides = result.stdout

    # Generate a simple configuration artifact
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
            "mender install /data/configuration-artifact.mender",
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

    # capture the new artifact and provides and verify they didn't change
    result = run(setup_tester_ssh_connection, "mender show-artifact 2>/dev/null",)
    new_artifact = result.stdout
    result = run(setup_tester_ssh_connection, "mender show-provides 2>/dev/null",)
    new_provides = result.stdout
    assert (new_artifact, new_provides) == (artifact, provides)


def test_mender_configure_managed_configuration(
    standard_setup_one_rofs_configure_client,
):
    # Make the mender-configure inventory script executable.
    # This is needed because ext4_manipulator.py doesn't support
    # setting permissions, and when we replace the inventory script
    # in install-mender-configure.py, we set permissions to 644 which
    # prevents the Mender Client executing it
    mender_device = standard_setup_one_rofs_configure_client.device
    mender_device.run("mount -o remount,rw /", wait=60)
    mender_device.run(
        "chmod 755 /usr/share/mender/inventory/mender-inventory-mender-configure",
        wait=60,
    )
    mender_device.run("mount -o remount,ro /", wait=60)

    # list of devices
    devices = list(
        set([device["id"] for device in devauth.get_devices_status("accepted")])
    )
    assert 1 == len(devices)

    # set the device's configuration
    configuration = {"key": "value"}
    configuration_url = (
        "https://%s/api/management/v1/deviceconfig/configurations/device/%s"
        % (get_container_manager().get_mender_gateway(), devices[0],)
    )
    auth = authentication.Authentication()
    r = requests_retry().put(
        configuration_url,
        verify=False,
        headers=auth.get_auth_token(),
        json=configuration,
    )

    # deploy the configurations
    r = requests_retry().post(
        configuration_url + "/deploy",
        verify=False,
        headers=auth.get_auth_token(),
        json={"retries": 0},
    )

    # loop and verify the reported configuration
    reported = None
    for i in range(180):
        r = requests_retry().get(
            configuration_url, verify=False, headers=auth.get_auth_token(),
        )
        assert r.status_code == 200
        reported = r.json().get("reported")
        if reported == configuration:
            break
        time.sleep(1)

    assert configuration == reported
