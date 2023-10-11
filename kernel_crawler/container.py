# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2023 The Falco Authors.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
    # http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import docker
import click

def decoded_str(s):
    if s is None:
        return ''
    return s.partition(b'\n')[0].decode("utf-8")

class Container():
    def __init__(self, image):
        self.image = image

    def run_cmd(self, cmd, encoding ="utf-8"):
        client = docker.from_env()
        container = client.containers.run(self.image, cmd, detach=True)
        logs = container.attach(stdout=True, stderr=True, stream=True, logs=True)
        # Depending on the command, the output could be buffered so first amalgamate
        # into one byte stream so that the outut can be processed correctly.
        with click.progressbar(logs, label='[' + self.image + '] Running command \'' + cmd + '\'', item_show_func=decoded_str) as logs:
            output = b''
            for line in logs:
                output += line
        decoded_line = output.decode(encoding)
        cmd_output = list(filter(None, decoded_line.split("\n")))
        return cmd_output
