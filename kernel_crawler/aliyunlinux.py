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
from . import rpm

def v2_only(ver):
    return ver.startswith('2')

def v3_only(ver):
    return ver.startswith('3')

class AliyunLinuxMirror(repo.Distro):
    def __init__(self, arch):
        mirrors = [
            # AliyunLinux 2
            # Mirror list on cloud-init config example:
            # https://www.alibabacloud.com/help/en/elastic-compute-service/latest/use-alibaba-cloud-linux-2-images-in-an-on-premises-environment
            rpm.RpmMirror('http://mirrors.aliyun.com/alinux/', 'os/' + arch + '/', v2_only),
            rpm.RpmMirror('http://mirrors.aliyun.com/alinux/', 'updates/' + arch + '/', v2_only),
            rpm.RpmMirror('http://mirrors.aliyun.com/alinux/', 'plus/' + arch + '/', v2_only),

            # AliyunLinux 3
            # Mirror list on cloud-init config example:
            # https://www.alibabacloud.com/help/en/elastic-compute-service/latest/use-alibaba-cloud-linux-3-images-in-an-on-premises-environment
            rpm.RpmMirror('http://mirrors.aliyun.com/alinux/', 'os/' + arch + '/', v3_only),
            rpm.RpmMirror('http://mirrors.aliyun.com/alinux/', 'updates/' + arch + '/', v3_only),
            rpm.RpmMirror('http://mirrors.aliyun.com/alinux/', 'plus/' + arch + '/', v3_only),

        ]
        super(AliyunLinuxMirror, self).__init__(mirrors, arch)

    def to_driverkit_config(self, release, deps):
        for dep in deps:
            if dep.find("devel") != -1:
                return repo.DriverKitConfig(release, "alinux", dep)
