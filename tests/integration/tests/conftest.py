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
#

import sys

from os import path

sys.path += [path.join(path.dirname(__file__), "..", "mender_integration")]

import logging
import random

import filelock
import pytest
import urllib3

from mender_integration.testutils.infra.container_manager import docker_compose_manager
from mender_integration.testutils.infra.device import MenderDevice
from mender_integration.tests.MenderAPI import devauth, reset_mender_api
from mender_test_containers.conftest import *
from mender_test_containers.container_props import *

logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("paramiko").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("filelock").setLevel(logging.INFO)
logging.getLogger("invoke").setLevel(logging.INFO)

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


collect_ignore = ["mender_integration"]

docker_lock = filelock.FileLock("docker_lock")
docker_compose_instance = "mender" + str(random.randint(0, 9999999))

inline_logs = False

MenderTestQemux86_64RofsMenderConfigure = ContainerProps(
    image_name="mendersoftware/mender-client-qemu-rofs-mender-configure",
    append_mender_version=False,
    key_filename=path.join(
        path.dirname(path.realpath(__file__)),
        "../mender_test_containers/docker/ssh-keys/key",
    ),
)

TEST_CONTAINER_LIST = [MenderTestQemux86_64RofsMenderConfigure]


@pytest.fixture(scope="session", params=TEST_CONTAINER_LIST)
def setup_test_container_props(request):
    return request.param


@pytest.fixture(scope="session")
def mender_version():
    return "master"


class DockerComposeStandardSetupOneConfigureRofsClient(
    docker_compose_manager.DockerComposeNamespace
):
    def __init__(
        self, extra_compose_file="../docker-compose.client.rofs.configure.yml"
    ):
        compose_files = docker_compose_manager.DockerComposeNamespace.QEMU_CLIENT_FILES
        compose_files += [
            path.join(path.dirname(__file__), extra_compose_file),
        ]
        docker_compose_manager.DockerComposeNamespace.__init__(
            self, name="mender", extra_files=compose_files
        )


@pytest.fixture(scope="function")
def standard_setup_one_rofs_configure_client(request):
    env = DockerComposeStandardSetupOneConfigureRofsClient()
    request.addfinalizer(env.teardown)

    env.setup()

    env.device = MenderDevice(env.get_mender_clients()[0])
    env.device.ssh_is_opened()

    reset_mender_api(env)
    devauth.accept_devices(1)

    return env
