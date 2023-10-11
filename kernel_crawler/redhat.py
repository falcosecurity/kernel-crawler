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

from . import repo
from .container import Container
import re

class RedhatContainer(repo.ContainerDistro):
    def __init__(self, image):
        super(RedhatContainer, self).__init__(image)

    def get_kernel_versions(self):
        kernels = {}
        c = Container(self.image)
        cmd_out = c.run_cmd("repoquery --show-duplicates kernel-devel")
        for log_line in cmd_out:
            m = re.search("(?<=kernel-devel-0:).*", log_line);
            if m:
                kernels[m.group(0)] = []
        return kernels

    def to_driverkit_config(self, release, deps):
        return repo.DriverKitConfig(release, "redhat", list(deps))
