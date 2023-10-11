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

def v7_only(ver):
    return ver.startswith('7')

def v8_only(ver):
    return ver.startswith('8')

def v9_only(ver):
    return ver.startswith('9')

def v6_or_v7(ver):
    return ver.startswith('6') or ver.startswith('7')

class CentosMirror(repo.Distro):
    def __init__(self, arch):
        mirrors = [
            # CentOS 6 + 7
            rpm.RpmMirror('http://vault.centos.org/centos/', 'os/' + arch + '/', v6_or_v7),
            rpm.RpmMirror('http://vault.centos.org/centos/', 'updates/' + arch + '/', v6_or_v7),
            rpm.RpmMirror('http://archive.kernel.org/centos/', 'os/' + arch + '/', v6_or_v7),
            rpm.RpmMirror('http://archive.kernel.org/centos/', 'updates/' + arch + '/', v6_or_v7),
            # CentOS 7
            rpm.RpmMirror('http://mirror.centos.org/centos/', 'os/' + arch + '/',  v7_only),
            rpm.RpmMirror('http://mirror.centos.org/centos/', 'updates/' + arch + '/', v7_only),
            # CentOS 8
            rpm.RpmMirror('http://mirror.centos.org/centos/', 'BaseOS/' + arch + '/os/', v8_only),
            rpm.RpmMirror('http://vault.centos.org/centos/', 'BaseOS/' + arch + '/os/', v8_only),
            rpm.RpmMirror('http://archive.kernel.org/centos/', 'BaseOS/' + arch + '/os/', v8_only),
            # CentOS 9
            rpm.RpmMirror('http://mirror.stream.centos.org/', 'BaseOS/' + arch + '/os/', v9_only),

            # It seems like stream variants uses /AppStream as well
            rpm.RpmMirror('http://archive.kernel.org/centos/', 'AppStream/' + arch + '/os/', v8_only),
            rpm.RpmMirror('http://mirror.stream.centos.org/', 'AppStream/' + arch + '/os/', v9_only),

            # These are some advanced mirrors for CentOS that enable newer kernels for ML
            rpm.RpmMirror('http://elrepo.org/linux/kernel/', f'{arch}/'),
            rpm.RpmMirror('http://mirrors.coreix.net/elrepo/kernel/', f'{arch}/'),
            rpm.RpmMirror('http://mirror.rackspace.com/elrepo/kernel/', f'{arch}/'),
            rpm.RpmMirror('http://linux-mirrors.fnal.gov/linux/elrepo/kernel/', f'{arch}/'),
        ]
        super(CentosMirror, self).__init__(mirrors, arch)

    def to_driverkit_config(self, release, deps):
        for dep in deps:
            if dep.find("devel") != -1:
                return repo.DriverKitConfig(release, "centos", dep)
