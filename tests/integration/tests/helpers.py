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
import subprocess
from os import path
import tempfile
import shutil

import pytest

from mender_integration.tests.MenderAPI import auth_v2, deploy

# Assume rootfsimage is in the this dir
ROOTFS_BASE_IMAGE = "mender-image-full-cmdline-rofs-qemux86-64.uefiimg.ext4"

# The helpers assume the tools are in the path
_MENDER_ARTIFACT_TOOL_PATH = "mender-artifact"
_DELTA_GENERATOR_TOOL_PATH = "mender-binary-delta-generator"


def make_rootfs_artifact(artifact_name, image, output_file, device_type="qemux86-64"):
    cmd = "%s write rootfs-image -f %s -t %s -n %s -o %s" % (
        _MENDER_ARTIFACT_TOOL_PATH,
        image,
        device_type,
        artifact_name,
        output_file,
    )
    logging.debug(cmd)

    subprocess.check_call(cmd, shell=True)


def add_file_to_artifact(artifact_file, local_file, remote_file):
    cmd = "%s cp %s %s:%s" % (
        _MENDER_ARTIFACT_TOOL_PATH,
        local_file,
        artifact_file,
        remote_file,
    )
    logging.debug(cmd)

    subprocess.check_call(cmd, shell=True)


def make_delta_artifact(
    artifact_name, artifact_from, artifact_to, output_file, transitional=False
):
    make_transitional = "--make-transitional" if transitional else ""
    cmd = "%s %s %s -n %s -o %s %s" % (
        _DELTA_GENERATOR_TOOL_PATH,
        artifact_from,
        artifact_to,
        artifact_name,
        output_file,
        make_transitional,
    )
    logging.debug(cmd)

    subprocess.check_call(cmd, shell=True)


def set_artifact_name(artifact, name):
    cmd = "mender-artifact modify -n %s %s" % (name, artifact,)
    logging.debug(cmd)
    subprocess.check_call(cmd, shell=True)


class DeltaArtifactsCreator:
    """Singleton class to create Delta Artifacts from a Base Artifact

    The Base Artifact is created at first invocation, creating a Mender Artifact from
    base rootfs image ROOTFS_BASE_IMAGE. From here, the class can create Delta Artifacts
    based on this one. See public methods.

    Obs! All Artifacts are created on a system tmpdir. The user must call cleanup() at the
    end to clear it
    """

    _instance = None
    _name_sequence = None
    _base_artifact_filename = None

    @staticmethod
    def get_instance():
        if DeltaArtifactsCreator._instance is None:
            DeltaArtifactsCreator()
        return DeltaArtifactsCreator._instance

    def __init__(self):
        self.tmpdir = tempfile.mkdtemp()
        self._write_rootfs_base_artifact()
        DeltaArtifactsCreator._instance = self

    def get_base_artifact_filename(self):
        return self._base_artifact_filename

    def _write_rootfs_base_artifact(self):
        self._base_artifact_filename = path.join(self.tmpdir, "artifact-base.mender")
        make_rootfs_artifact(
            artifact_name="test-base",
            image=ROOTFS_BASE_IMAGE,
            output_file=self._base_artifact_filename,
        )

    def _next_artifact_filename(self):
        if self._name_sequence is None:
            self._name_sequence = tempfile._RandomNameSequence()
        rnd_namme = next(self._name_sequence)
        return path.join(self.tmpdir, rnd_namme + ".mender")

    def make_delta_artifact(self, artifact_name, artifact_to, transitional=False):
        """Create new Delta Artifact update from the Base Artifact to the given one

        Returns the filename of the created Artifact.
        """
        output_file = self._next_artifact_filename()
        make_delta_artifact(
            artifact_name,
            self._base_artifact_filename,
            artifact_to,
            output_file,
            transitional=transitional,
        )
        return output_file

    def make_rootfs_artifact_with_file(
        self, local_file, remote_file, artifact_name=None
    ):
        """Create new Rootfs Artifact from the Base Artifact adding the given file to the given location

        Returns the filename of the created Artifact.
        """
        next_artifact = self._next_artifact_filename()
        shutil.copy(self._base_artifact_filename, next_artifact)
        add_file_to_artifact(next_artifact, local_file, remote_file)
        if artifact_name is not None:
            set_artifact_name(next_artifact, artifact_name)
        return next_artifact

    def make_delta_artifact_with_file(
        self, delta_artifact_name, local_file, remote_file, transitional=False
    ):
        """Create new Delta Artifact from the Base Artifact to one containing the given file in the given location

        Internally, it will first create a "next" Artifat with the given file, and then create the delta to it.
        Returns the filename of the created Artifact.
        """
        next_artifact = self.make_rootfs_artifact_with_file(local_file, remote_file)
        return self.make_delta_artifact(
            delta_artifact_name, next_artifact, transitional=transitional
        )

    def cleanup(self):
        shutil.rmtree(self.tmpdir)
        DeltaArtifactsCreator._instance = None


def bootstrap_client_with_provides_artifact():
    """
    Bootstrap a client by deploying an artifact that has correct
    artifact_provides for a rootfs-image.
    """

    rootfs_artifact_filename = (
        DeltaArtifactsCreator.get_instance().get_base_artifact_filename()
    )
    logging.debug("Created the base artifact: %s" % rootfs_artifact_filename)

    deploy.upload_image(rootfs_artifact_filename)
    devices = list(
        set([device["id"] for device in auth_v2.get_devices_status("accepted")])
    )
    deployment_id = deploy.trigger_deployment(
        name="test-base", artifact_name="test-base", devices=devices
    )

    # Check finished status only from server point of view
    deploy.check_expected_status("finished", deployment_id)
