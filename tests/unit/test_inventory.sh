#! /bin/sh
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
test_dir="$(dirname $0)"
tmp_dir="$(mktemp -d)"
state_dir="$(mktemp -d)"
inv_script="${test_dir}/../../src/mender-inventory-mender-configure"

# Override variables inside the inventory script.
export TEST_CONFIG="${state_dir}/device-config.json"
export TEST_CONFIG_CHECKSUM="${state_dir}/device-config-reported.sha256"
export TEST_HTTP_LOG="${tmp_dir}/http.log"

oneTimeSetUp() {
    "${test_dir}/helpers/mender-configure-server.py" &
    TEST_SERVER_PID=$!
    sleep 1
}

oneTimeTearDown() {
    # For some reason this sometimes returns failure, but the process *is*
    # killed.
    kill $TEST_SERVER_PID || true
}

setUp() {
    OLD_PATH="$PATH"
    export PATH="${test_dir}/helpers:$PATH"

    export TEST_SERVER_URL=http://localhost:8080

    mkdir -p "${tmp_dir}"
    mkdir -p "${state_dir}"

    echo '{"old":"value"}' > "${TEST_CONFIG}"
}

tearDown() {
    rm -rf "${state_dir}" "${tmp_dir}"
    export PATH="$OLD_PATH"
    unset TEST_SERVER_URL
    unset TEST_SERVER_URL_EMPTY
    unset TEST_CONFIG_ENDPOINT
    unset TEST_AUTH_TOKEN_EMPTY
    unset TEST_AUTH_TOKEN
}

testSuccessfulReport() {
    output="$("${inv_script}")"
    assertEquals 0 $?
    # Script should never return output on stdout, this goes for all the test
    # cases.
    assertEquals "" "${output}"
    assertEquals 'Log: path = "/api/devices/v1/deviceconfig/configuration", auth_token = "Bearer ThisIsAnAuthToken"' "$(cat "$TEST_HTTP_LOG")"
}

testInvalidEndpoint() {
    export TEST_CONFIG_ENDPOINT=nonexisting
    output="$("${inv_script}")"
    assertNotEquals 0 $?
    assertEquals "" "${output}"
    assertEquals 'Log: path = "/nonexisting", auth_token = "Bearer ThisIsAnAuthToken"' "$(cat "$TEST_HTTP_LOG")"
}

testMissingJwtToken() {
    export TEST_AUTH_TOKEN_EMPTY=1
    output="$("${inv_script}")"
    assertNotEquals 0 $?
    assertEquals "" "${output}"
    assertEquals "" "$(cat "$TEST_HTTP_LOG" 2>/dev/null)"
}

testWrongJwtToken() {
    export TEST_AUTH_TOKEN=WrongToken
    output="$("${inv_script}")"
    assertNotEquals 0 $?
    assertEquals "" "${output}"
    assertEquals 'Log: path = "/api/devices/v1/deviceconfig/configuration", auth_token = "Bearer WrongToken"' "$(cat "$TEST_HTTP_LOG")"
}

testMissingServer() {
    export TEST_SERVER_URL_EMPTY=1
    output="$("${inv_script}")"
    assertNotEquals 0 $?
    assertEquals "" "${output}"
    assertEquals "" "$(cat "$TEST_HTTP_LOG" 2>/dev/null)"
}

testWrongServer() {
    export TEST_SERVER_URL="http://localhost:12345"
    output="$("${inv_script}")"
    assertNotEquals 0 $?
    assertEquals "" "${output}"
    assertEquals "" "$(cat "$TEST_HTTP_LOG" 2>/dev/null)"
}

testReportCaching() {
    output="$("${inv_script}")"
    assertEquals 0 $?
    assertEquals "" "${output}"
    assertEquals 'Log: path = "/api/devices/v1/deviceconfig/configuration", auth_token = "Bearer ThisIsAnAuthToken"' "$(cat "$TEST_HTTP_LOG")"

    output="$("${inv_script}")"
    assertEquals 0 $?
    assertEquals "" "${output}"
    # Despite being called a second time, the caching should have kicked in and
    # prevented reporting.
    assertEquals 'Log: path = "/api/devices/v1/deviceconfig/configuration", auth_token = "Bearer ThisIsAnAuthToken"' "$(cat "$TEST_HTTP_LOG")"

    # Change the config.
    echo '{"new":"value"}' > "${TEST_CONFIG}"

    output="$("${inv_script}")"
    assertEquals 0 $?
    assertEquals "" "${output}"
    # Now there should be a second report.
    assertEquals 'Log: path = "/api/devices/v1/deviceconfig/configuration", auth_token = "Bearer ThisIsAnAuthToken"
Log: path = "/api/devices/v1/deviceconfig/configuration", auth_token = "Bearer ThisIsAnAuthToken"' "$(cat "$TEST_HTTP_LOG")"

    output="$("${inv_script}")"
    assertEquals 0 $?
    assertEquals "" "${output}"
    # But no third report.
    assertEquals 'Log: path = "/api/devices/v1/deviceconfig/configuration", auth_token = "Bearer ThisIsAnAuthToken"
Log: path = "/api/devices/v1/deviceconfig/configuration", auth_token = "Bearer ThisIsAnAuthToken"' "$(cat "$TEST_HTTP_LOG")"

    # Change the auth token
    export TEST_AUTH_TOKEN="ThisIsAnotherAuthToken"

    output="$("${inv_script}")"
    assertEquals 0 $?
    assertEquals "" "${output}"
    # Now there should be a third report.
    assertEquals 'Log: path = "/api/devices/v1/deviceconfig/configuration", auth_token = "Bearer ThisIsAnAuthToken"
Log: path = "/api/devices/v1/deviceconfig/configuration", auth_token = "Bearer ThisIsAnAuthToken"
Log: path = "/api/devices/v1/deviceconfig/configuration", auth_token = "Bearer ThisIsAnotherAuthToken"' "$(cat "$TEST_HTTP_LOG")"
}


# Load and run shUnit2.
. ${test_dir}/shunit2/shunit2
