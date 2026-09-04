# Copyright 2026 Northern.tech AS
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

sys.path.insert(0, path.abspath(path.dirname(__file__)))

import logging
import pytest
import urllib3

from mender_testkit.server import Server
from mender_testkit.docker import docker_compose_stop
from mender_testkit.devices import (
    Env,
    clients_up,
    wait_for_devices,
    client_compose_env,
    project_name_client,
)

from mender_test_containers.conftest import *
from mender_test_containers.container_props import *

logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("paramiko").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("filelock").setLevel(logging.INFO)
logging.getLogger("invoke").setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

machine_name = "qemux86-64"
inline_logs = False

# The backend lifecycle -- os_backend_server and enterprise_backend_server -- comes
# from mender_testkit's pytest plugin, which also decides which compose files to
# use.

CLIENT_COMPOSE_FILE = "docker-compose.client.rofs.configure.yml"


@pytest.fixture(scope="function", autouse=True)
def devices_down():
    yield
    # The client compose file declares the backend network as external, so teardown has to resolve
    # it to the same name clients_up used.
    docker_compose_stop(
        project_name=project_name_client,
        files=[CLIENT_COMPOSE_FILE],
        env=client_compose_env(),
    )


# -------------------------------------------------------------------------

MenderTestQemux86_64RofsMenderConfigure = ContainerProps(
    image_name="mendersoftware/mender-client-qemu-rofs-mender-configure",
    append_mender_version=False,
    key_filename=path.join(
        path.dirname(path.realpath(__file__)),
        "../mender_test_containers/qemu-test-containers/ssh-keys/key",
    ),
)

TEST_CONTAINER_LIST = [MenderTestQemux86_64RofsMenderConfigure]


@pytest.fixture(scope="session", params=TEST_CONTAINER_LIST)
def setup_test_container_props(request):
    return request.param


@pytest.fixture(scope="session")
def mender_version():
    return "master"


@pytest.fixture(scope="function")
def standard_setup_one_rofs_configure_client(request, os_backend_server):
    env = Env()
    server = Server()
    env.server = server

    env.devices = clients_up(1, CLIENT_COMPOSE_FILE, network=server.network)
    env.device = env.devices[0]

    wait_for_devices(env)

    server.accept_devices(env.devices)
    assert 1 == len(server.get_accepted_devices())

    return env
