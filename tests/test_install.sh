#! /bin/sh

test_dir=$(dirname $0)
mender_configure=${test_dir}/../src/mender-configure


testArtifactInstallDummy() {
    output=$(./$mender_configure ArtifactInstall /tmp/nonexisting)
    exit_code=$?
    assertEquals 0 $exit_code
    assertEquals "Dummy install" "${output}"
}


# Load and run shUnit2.
. ${test_dir}/shunit2/shunit2
