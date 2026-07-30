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
"""Management-API facade over a mender-server backend brought up by compose.

Kept identical across mender-binary-delta, mender-configure-module,
mender-gateway and mender-orchestrator; the only per-repo difference is the
import root for testutils. This is an API client only: it does not start, stop
or otherwise own the backend. Bringing the stack up is the conftest's job, and
the compose project it used is the single thing this class needs to be told.
"""

import logging
import os
import subprocess
import uuid

import redo

from helpers import docker_lock, get_mac_address
from testutils.api import (
    deployments,
    deviceauth,
    deviceconfig,
    inventory,
    tenantadm,
    useradm,
)
from testutils.api.client import ApiClient
from testutils.common import create_user

logger = logging.getLogger(__name__)

# Traefik's routers match on Host as well as path. We address the ingress by
# container IP, so every request has to carry this or no router matches and the
# gateway answers 404.
HOST_NAME = "docker.mender.io"

# Compose project per plan, so an OS and an enterprise backend can be up at the
# same time without colliding. Repos that only ever run one backend get "mender",
# which is the name they used to hardcode.
SERVER_PROJECTS = {
    "os": "mender",
    "enterprise": "mender_enterprise",
}

# An unauthenticated GET on the login route answers with one of these once the
# ingress routes and useradm's HTTP server is listening.
_READY_STATUS_CODES = (200, 401, 405)


def server_project(plan):
    return SERVER_PROJECTS[plan]


def server_network(plan):
    """Name of the network the backend's containers are attached to."""
    return f"{SERVER_PROJECTS[plan]}_default"


def get_server_host(project):
    """IP of the ingress container for `project`.

    Retried: immediately after `compose up` the container exists but has not
    been given an address on the network yet.
    """
    container = f"{project}-traefik-1"

    def _get_host():
        with docker_lock:
            address = (
                subprocess.check_output(
                    f"docker inspect {container} "
                    "--format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'",
                    shell=True,
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .strip()
            )
        if not address:
            raise ValueError(f"{container} has no address yet")
        return address

    return redo.retry(_get_host, attempts=30, sleeptime=2)


def _poll_login(client, attempts, sleeptime):
    def _check_ready():
        r = client.call("GET", useradm.URL_LOGIN)
        if r.status_code not in _READY_STATUS_CODES:
            raise ValueError(f"backend not ready yet, status: {r.status_code}")
        return True

    return redo.retry(
        _check_ready,
        attempts=attempts,
        sleeptime=sleeptime,
        max_sleeptime=sleeptime,
        sleepscale=1,
    )


def wait_for_backend_ready(project, attempts=60, sleeptime=2):
    """Block until the ingress routes and useradm answers API requests.

    mender-server declares healthchecks only on traefik, mongo, nats and s3, so
    `up --wait` returns while the Go services are still binding their ports.

    Every xdist worker calls this, not just the one that started the backend, so
    that workers which did not start it don't race ahead into a half-booted
    stack.
    """
    client = ApiClient(useradm.URL_MGMT, get_server_host(project)).with_header(
        "Host", HOST_NAME
    )
    logger.info("waiting for the %s backend to become ready", project)
    return _poll_login(client, attempts=attempts, sleeptime=sleeptime)


class Server:
    """Management API client for one backend.

    `plan` selects both the compose project to address and whether a tenant is
    provisioned through tenantadm (enterprise) or a bare user through useradm
    (open source).
    """

    def __init__(self, plan="os"):
        self.plan = plan
        self.project_name = SERVER_PROJECTS[plan]
        # Kept under the old name too: testutils' CLI wrappers take it as
        # `containers_namespace`.
        self.containers_namespace = self.project_name
        self.network = server_network(plan)
        self.host_ip = get_server_host(self.project_name)
        self.host_name = HOST_NAME
        self.deployment_id = ""
        self.tenant_id = None

        # The Host header is set explicitly on every client: testutils' ApiClient
        # does not add one, and even where a fork of it does, hardcoding the
        # module-level default would ignore an overridden self.host_name.
        self.useradm = self._client(useradm.URL_MGMT)
        self.deployments = self._client(deployments.URL_MGMT)
        self.devauth = self._client(deviceauth.URL_MGMT)
        self.tenantadm = self._client(tenantadm.URL_MGMT)
        self.inventory = self._client(inventory.URL_MGMT)
        self.deviceconfig = self._client(deviceconfig.URL_MGMT)

        self._provision_tenant()
        self.auth_token = self.get_auth_token()

    def _client(self, base_url):
        return ApiClient(base_url, host=self.host_ip).with_header(
            "Host", self.host_name
        )

    # ---------------------------------------------------------------- readiness

    def wait_for_useradm_ready(self, attempts=20, sleeptime=2):
        """Poll useradm until its HTTP server accepts connections."""
        logger.info("waiting for useradm to be ready")
        return _poll_login(self.useradm, attempts=attempts, sleeptime=sleeptime)

    # ------------------------------------------------------------------- tenant

    def _provision_tenant(self):
        uuidv4 = str(uuid.uuid4())
        self.username = f"some.user+{uuidv4}@example.com"
        self.password = "secretsecret"

        if self.plan != "enterprise":
            create_user(
                self.username,
                self.password,
                containers_namespace=self.containers_namespace,
            )
            return

        # Addressed by container name rather than through testutils' CliTenantadm:
        # that resolves the container by grepping `docker ps` for the project
        # name, and "mender" is a substring of "mender_enterprise".
        cmd = [
            "docker",
            "exec",
            f"{self.containers_namespace}-tenantadm-1",
            "/usr/bin/tenantadm",
            "create-org",
            "--name",
            f"test.tenant+{uuidv4}",
            "--username",
            self.username,
            "--password",
            self.password,
            "--device-limit",
            "100",
        ]

        def _create_org():
            return subprocess.check_output(cmd).decode("utf-8").strip()

        # Connection-refused errors here mean useradm is still coming up.
        self.wait_for_useradm_ready()
        logger.info("provisioning enterprise tenant")
        self.tenant_id = redo.retry(
            _create_org, attempts=5, sleeptime=5, max_sleeptime=30
        )
        logger.info("created tenant %s", self.tenant_id)

    def get_auth_token(self):
        def _get_auth_token():
            r = self.useradm.call(
                "POST", useradm.URL_LOGIN, auth=(self.username, self.password)
            )
            if r.status_code == 200:
                assert r.text, "login returned an empty token"
                return r.text
            # 404/502/503 while Traefik is still wiring up its routers.
            raise ValueError(f"server not ready, got status: {r.status_code}")

        return redo.retry(
            _get_auth_token,
            sleeptime=2,
            max_sleeptime=2,
            sleepscale=1,
            attempts=15,
        )

    def get_tenant_token(self):
        r = self.tenantadm.with_auth(self.auth_token).call(
            "GET", tenantadm.URL_MGMT_THIS_TENANT
        )
        assert r.status_code == 200, f"{r.text} {r.status_code}"
        return r.json()["tenant_token"]

    # ------------------------------------------------------------------ devices

    def get_pending_devices(self):
        return self._get_devices("pending")

    def get_accepted_devices(self):
        return self._get_devices("accepted")

    def _get_devices(self, status):
        r = self.devauth.with_auth(self.auth_token).call(
            "GET",
            deviceauth.URL_MGMT_DEVICES,
            qs_params={"page": 1, "per_page": 64, "status": status},
        )
        assert r.status_code == 200, f"{r.text} {r.status_code}"
        return r.json()

    def accept_devices(
        self,
        devices,
        sleeptime=2,
        sleepscale=1,
        max_sleeptime=10,
        max_attempts=30,
    ):
        """Accept each device's first auth set; return their ids in input order.

        The retry parameters are exposed because a device behind mender-gateway
        takes far longer to show up than a directly connected one.
        """
        # Resolved once rather than per attempt: get_mac_address talks to the
        # device over SSH, and on failure a per-attempt call would multiply that
        # timeout by the number of devices and the number of attempts. A failure
        # here propagates instead of being swallowed by the retry.
        mac_addresses = [get_mac_address(device) for device in devices]

        # Accumulated across attempts: a device accepted on attempt N is gone
        # from the pending list by attempt N+1, so counting only what the current
        # attempt saw would never reach the target and would return short.
        accepted = {}

        def _accept_devices():
            for device in self.get_pending_devices():
                mac = device["identity_data"].get("mac")
                if mac not in mac_addresses or mac in accepted:
                    continue
                r = self.devauth.with_auth(self.auth_token).call(
                    "PUT",
                    deviceauth.URL_AUTHSET_STATUS,
                    deviceauth.req_status("accepted"),
                    path_params={
                        "did": device["id"],
                        "aid": device["auth_sets"][0]["id"],
                    },
                )
                assert r.status_code == 204, f"{r.text} {r.status_code}"
                accepted[mac] = device["id"]

            if len(accepted) != len(mac_addresses):
                raise ValueError(
                    f"accepted {len(accepted)} of {len(mac_addresses)} device(s), "
                    f"still waiting for {sorted(set(mac_addresses) - set(accepted))}"
                )
            return [accepted[mac] for mac in mac_addresses]

        return redo.retry(
            _accept_devices,
            sleeptime=sleeptime,
            sleepscale=sleepscale,
            max_sleeptime=max_sleeptime,
            attempts=max_attempts,
        )

    # ------------------------------------------------------------ configuration

    def set_device_configuration(self, device_id, configuration):
        r = self.deviceconfig.with_auth(self.auth_token).call(
            "PUT",
            deviceconfig.URL_MGMT_DEVICE_CONFIGURATION,
            body=configuration,
            path_params={"id": device_id},
        )
        assert r.status_code == 204, f"{r.text} {r.status_code}"

    def get_device_configuration(self, device_id):
        r = self.deviceconfig.with_auth(self.auth_token).call(
            "GET",
            deviceconfig.URL_MGMT_DEVICE_CONFIGURATION,
            path_params={"id": device_id},
        )
        assert r.status_code == 200, f"{r.text} {r.status_code}"
        return r.json()

    def deploy_device_configuration(self, device_id, retries=0):
        r = self.deviceconfig.with_auth(self.auth_token).call(
            "POST",
            deviceconfig.URL_MGMT_DEVICE_CONFIGURATION_DEPLOY,
            body={"retries": retries},
            path_params={"id": device_id},
        )
        assert r.status_code == 200, f"{r.text} {r.status_code}"
        return r.json()

    # -------------------------------------------------------------- deployments

    def upload_image(self, filename):
        r = self.deployments.with_auth(self.auth_token).call(
            "POST",
            deployments.URL_DEPLOYMENTS_ARTIFACTS,
            files=(
                ("description", (None)),
                ("size", (None, str(os.path.getsize(filename)))),
                (
                    "artifact",
                    (filename, open(filename, "rb"), "application/octet-stream"),
                ),
            ),
        )
        # 409 means an artifact with this name and depends/provides is already
        # stored, which is benign for suites that upload the same one twice.
        assert r.status_code in (201, 409), f"{r.text} {r.status_code}"
        if r.status_code == 409:
            logger.info("artifact %s already present on the server", filename)

    def create_deployment(self, artifact_name, device_ids):
        logger.info("creating deployment for %s", artifact_name)
        r = self.deployments.with_auth(self.auth_token).call(
            "POST",
            deployments.URL_DEPLOYMENTS,
            body={
                "name": artifact_name,
                "artifact_name": artifact_name,
                "devices": device_ids,
            },
        )
        assert r.status_code == 201, f"{r.text} {r.status_code}"
        self.deployment_id = os.path.basename(r.headers["Location"])
        return self.deployment_id

    def _get_deployment(self, deployment_id):
        r = self.deployments.with_auth(self.auth_token).call(
            "GET", deployments.URL_DEPLOYMENTS_ID.format(id=deployment_id)
        )
        assert r.status_code == 200, f"{r.text} {r.status_code}"
        return r.json()

    def check_expected_statistics(
        self,
        deployment_id,
        expected_status,
        expected_mender_clients,
        max_sleeptime=60,
        max_attempts=10,
    ):
        def _check_expected_statistics():
            status = (
                self._get_deployment(deployment_id)
                .get("statistics", {})
                .get("status", {})
            )
            assert expected_mender_clients == int(status.get(expected_status, 0)), (
                f"expected {expected_mender_clients} client(s) in state "
                f"'{expected_status}', deployment statistics are: {status}"
            )

        return redo.retry(
            _check_expected_statistics,
            sleeptime=5,
            sleepscale=2,
            max_sleeptime=max_sleeptime,
            attempts=max_attempts,
        )

    def check_expected_status(
        self, expected_status, deployment_id, max_sleeptime=60, max_attempts=10
    ):
        def _check_expected_status():
            actual = self._get_deployment(deployment_id)["status"]
            assert (
                actual == expected_status
            ), f"expected deployment status '{expected_status}', got '{actual}'"

        return redo.retry(
            _check_expected_status,
            sleeptime=5,
            sleepscale=2,
            max_sleeptime=max_sleeptime,
            attempts=max_attempts,
        )

    def get_deployment_logs(self, device_id, deployment_id):
        r = self.deployments.with_auth(self.auth_token).call(
            "GET", f"/deployments/{deployment_id}/devices/{device_id}/log"
        )
        assert r.status_code == 200, f"{r.text} {r.status_code}"
        return r.text

    def abort_deployment(self, deployment_id):
        r = self.deployments.with_auth(self.auth_token).call(
            "PUT",
            f"/deployments/{deployment_id}/status",
            body={"status": "aborted"},
        )
        assert r.status_code == 204, f"{r.text} {r.status_code}"
