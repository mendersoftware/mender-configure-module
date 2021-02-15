#!/usr/bin/env python3
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

import http.server as server
import os


class MenderConfigureHandler(server.BaseHTTPRequestHandler):
    def do_PUT(self):
        auth = self.headers.get("Authorization", "")

        if self.path != "/api/devices/v1/deviceconfig/configuration":
            response = 404
        elif auth != "Bearer ThisIsAnAuthToken":
            response = 401
        else:
            response = 204
        self.send_response(response)

        http_log_path = os.environ.get("TEST_HTTP_LOG")
        if http_log_path is None:
            http_log_path = "./http.log"
        with open(http_log_path, "a") as log:
            log.write(f'Log: path = "{self.path}", auth_token = "{auth}"')

        self.end_headers()


if __name__ == "__main__":
    s = server.HTTPServer(("", 8080), MenderConfigureHandler)
    s.serve_forever()
