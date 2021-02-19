#! /bin/sh

test_dir="$(dirname $0)"
tmp_dir="$(mktemp -d)"
state_dir="$(mktemp -d)"
module_dir="${state_dir}/module"
applycmd_dir="$(mktemp -d)/apply-device-config.d"
applycmd="${applycmd_dir}/apply-device-config"
applycmd_log="${tmp_dir}/apply-device-config.log"
mender_configure="${test_dir}/../src/mender-configure"

# Override variables inside the Update Module.
export TEST_CONFIG="${state_dir}/device-config.json"
export TEST_APPLY_DIR="${applycmd_dir}"

# Makes it easier to do output matching.
export QUIET=1

setUp() {
    mkdir -p "${tmp_dir}"
    mkdir -p "${state_dir}"
    mkdir -p "${applycmd_dir}"
    mkdir -p "${module_dir}/tmp"

    cat > "${applycmd}" <<EOF
#!/bin/sh

echo "\$(basename "\$0")" "\$@" >> "${applycmd_log}"
EOF
    chmod ugo+x "${applycmd}"

    mkdir -p "${module_dir}/header"
    cat > "${module_dir}/header/meta-data" <<EOF
{"new":"value"}
EOF

    echo '{"old":"value"}' > "${TEST_CONFIG}"
}

tearDown() {
    rm -rf "${state_dir}" "${applycmd_dir}" "${tmp_dir}"
}


testOtherState() {
    output="$(./$mender_configure Download "${module_dir}")"
    assertEquals 0 $?
    assertEquals "" "${output}"
}

testFreshArtifactInstall() {
    rm -f "${TEST_CONFIG}"

    output="$(./$mender_configure ArtifactInstall "${module_dir}")"
    assertEquals 0 $?
    assertEquals "" "${output}"

    assertEquals '{"new":"value"}' "$(cat "${TEST_CONFIG}")"
    assertEquals "apply-device-config ${TEST_CONFIG}" "$(cat "${applycmd_log}")"
}

testArtifactInstallConfigExists() {
    output="$(./$mender_configure ArtifactInstall "${module_dir}")"
    assertEquals 0 $?
    assertEquals "" "${output}"

    assertEquals '{"new":"value"}' "$(cat "${TEST_CONFIG}")"
    assertEquals "apply-device-config ${TEST_CONFIG}" "$(cat "${applycmd_log}")"
}

testNeedsArtifactRebootAutomatic() {
    echo 'exit 20' >> "${applycmd}"

    output="$(./$mender_configure ArtifactInstall "${module_dir}")"
    assertEquals 0 $?
    assertEquals "" "${output}"

    output="$(./$mender_configure NeedsArtifactReboot "${module_dir}")"
    assertEquals 0 $?
    assertEquals "Automatic" "${output}"

    assertEquals '{"new":"value"}' "$(cat "${TEST_CONFIG}")"
    assertEquals "apply-device-config ${TEST_CONFIG}" "$(cat "${applycmd_log}")"
}

testNeedsArtifactRebootNo() {
    output="$(./$mender_configure ArtifactInstall "${module_dir}")"
    assertEquals 0 $?
    assertEquals "" "${output}"

    output="$(./$mender_configure NeedsArtifactReboot "${module_dir}")"
    assertEquals 0 $?
    assertEquals "No" "${output}"

    assertEquals '{"new":"value"}' "$(cat "${TEST_CONFIG}")"
    assertEquals "apply-device-config ${TEST_CONFIG}" "$(cat "${applycmd_log}")"
}

testNeedsArtifactRebootStandalone() {
    output="$(./$mender_configure NeedsArtifactReboot "${module_dir}")"
    assertEquals 0 $?
    assertEquals "No" "${output}"

    assertEquals '{"old":"value"}' "$(cat "${TEST_CONFIG}")"
    assertEquals "" "$(cat "${applycmd_log}" 2>/dev/null)"
}

testArtifactCommit() {
    output="$(./$mender_configure ArtifactInstall "${module_dir}")"
    assertEquals 0 $?
    assertEquals "" "${output}"

    output="$(./$mender_configure NeedsArtifactReboot "${module_dir}")"
    assertEquals 0 $?
    assertEquals "No" "${output}"

    output="$(./$mender_configure ArtifactCommit "${module_dir}")"
    assertEquals 0 $?
    assertEquals "" "${output}"

    assertEquals '{"new":"value"}' "$(cat "${TEST_CONFIG}")"
    assertEquals "apply-device-config ${TEST_CONFIG}" "$(cat "${applycmd_log}")"
}

testArtifactRollback() {
    output="$(./$mender_configure SupportsRollback "${module_dir}")"
    assertEquals 0 $?
    assertEquals "Yes" "${output}"

    output="$(./$mender_configure ArtifactInstall "${module_dir}")"
    assertEquals 0 $?
    assertEquals "" "${output}"

    output="$(./$mender_configure NeedsArtifactReboot "${module_dir}")"
    assertEquals 0 $?
    assertEquals "No" "${output}"

    output="$(./$mender_configure ArtifactRollback "${module_dir}")"
    assertEquals 0 $?
    assertEquals "" "${output}"

    assertEquals '{"old":"value"}' "$(cat "${TEST_CONFIG}")"
    assertEquals "apply-device-config ${TEST_CONFIG}
apply-device-config ${TEST_CONFIG}" "$(cat "${applycmd_log}")"
}

testArtifactRollbackAndReboot() {
    echo 'if [ "$TEST_ROLLBACK" = 1 ]; then exit 20; fi' >> "${applycmd}"

    output="$(./$mender_configure ArtifactInstall "${module_dir}")"
    assertEquals 0 $?
    assertEquals "" "${output}"

    output="$(./$mender_configure NeedsArtifactReboot "${module_dir}")"
    assertEquals 0 $?
    assertEquals "No" "${output}"

    export TEST_ROLLBACK=1
    output="$(./$mender_configure ArtifactRollback "${module_dir}")"
    assertEquals 0 $?
    assertEquals "" "${output}"
    unset TEST_ROLLBACK

    output="$(./$mender_configure NeedsArtifactReboot "${module_dir}")"
    assertEquals 0 $?
    assertEquals "Automatic" "${output}"

    assertEquals '{"old":"value"}' "$(cat "${TEST_CONFIG}")"
    assertEquals "apply-device-config ${TEST_CONFIG}
apply-device-config ${TEST_CONFIG}" "$(cat "${applycmd_log}")"
}

testRollbackNoOriginalConfiguration() {
    rm -f "${TEST_CONFIG}"

    output="$(./$mender_configure SupportsRollback "${module_dir}")"
    assertEquals 0 $?
    assertEquals "Yes" "${output}"

    output="$(./$mender_configure ArtifactInstall "${module_dir}")"
    assertEquals 0 $?
    assertEquals "" "${output}"

    output="$(./$mender_configure ArtifactRollback "${module_dir}")"
    assertEquals 0 $?
    assertEquals "" "${output}"

    assertFalse "test -e ${TEST_CONFIG}"
    assertEquals "apply-device-config ${TEST_CONFIG}" "$(cat "${applycmd_log}")"
}

testMixedSuccessAndFailure() {
    rm -f "${applycmd}"
    printf '#!/bin/sh\nexit 0\n' > "${applycmd_dir}/00"
    printf '#!/bin/sh\nexit 3\n' > "${applycmd_dir}/01"
    printf '#!/bin/sh\nexit 0\n' > "${applycmd_dir}/02"
    chmod ugo+x "${applycmd_dir}"/*

    output="$(./$mender_configure ArtifactInstall "${module_dir}")"
    assertEquals 3 $?
    assertEquals "" "${output}"
}

testMixedSuccessAndReboot() {
    rm -f "${applycmd}"
    printf '#!/bin/sh\nexit 0\n' > "${applycmd_dir}/00"
    printf '#!/bin/sh\nexit 20\n' > "${applycmd_dir}/01"
    printf '#!/bin/sh\nexit 0\n' > "${applycmd_dir}/02"
    chmod ugo+x "${applycmd_dir}"/*

    output="$(./$mender_configure ArtifactInstall "${module_dir}")"
    assertEquals 0 $?
    assertEquals "" "${output}"
}

testMixedFailureAndReboot() {
    rm -f "${applycmd}"
    printf '#!/bin/sh\nexit 3\n' > "${applycmd_dir}/00"
    printf '#!/bin/sh\nexit 20\n' > "${applycmd_dir}/01"
    printf '#!/bin/sh\nexit 0\n' > "${applycmd_dir}/02"
    chmod ugo+x "${applycmd_dir}"/*

    output="$(./$mender_configure ArtifactInstall "${module_dir}")"
    assertEquals 3 $?
    assertEquals "" "${output}"
}

testMixedFailureAndReboot2() {
    rm -f "${applycmd}"
    printf '#!/bin/sh\nexit 20\n' > "${applycmd_dir}/00"
    printf '#!/bin/sh\nexit 3\n' > "${applycmd_dir}/01"
    printf '#!/bin/sh\nexit 0\n' > "${applycmd_dir}/02"
    chmod ugo+x "${applycmd_dir}"/*

    output="$(./$mender_configure ArtifactInstall "${module_dir}")"
    assertEquals 3 $?
    assertEquals "" "${output}"
}


# Load and run shUnit2.
. ${test_dir}/shunit2/shunit2
