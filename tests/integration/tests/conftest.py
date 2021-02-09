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

import sys

from os import path

sys.path += [path.join(path.dirname(__file__), "..", "mender_integration")]

import logging
import random

import filelock
import pytest
import urllib3

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
