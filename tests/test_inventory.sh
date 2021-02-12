#! /bin/sh

test_dir="$(dirname $0)"
tmp_dir="$(mktemp -d)"
state_dir="$(mktemp -d)"
inv_script="${test_dir}/../src/mender-inventory-mender-configure"

# Override variables inside the inventory script.
export TEST_CONFIG="${state_dir}/device-config.json"
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


# Load and run shUnit2.
. ${test_dir}/shunit2/shunit2
