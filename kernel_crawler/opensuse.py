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

def tumbleweed_filter(dist):
    return dist.startswith('tumbleweed') or \
        dist.startswith('./tumbleweed')


class OpenSUSEMirror(repo.Distro):


    def __init__(self, arch):
        mirrors = [
            # leap
            rpm.SUSERpmMirror('https://mirrors.edge.kernel.org/opensuse/distribution/leap/', 'repo/oss/', arch),
            rpm.SUSERpmMirror('https://mirrors.edge.kernel.org/opensuse/distribution/leap/', 'repo/oss/suse/', arch),
            # the rest
            rpm.SUSERpmMirror('https://mirrors.edge.kernel.org/opensuse/distribution/', 'repo/oss/', arch),
            rpm.SUSERpmMirror('https://mirrors.edge.kernel.org/opensuse/distribution/', 'repo/oss/suse/', arch),
            # opensuse site: tumbleweed -> enforce zstd for repo:
            # https://lists.opensuse.org/archives/list/factory@lists.opensuse.org/thread/LJNSBPCMIOJMP37PFPV7C7EJVIOW26BN/
            rpm.SUSERpmMirror('http://download.opensuse.org/', 'repo/oss/', arch, tumbleweed_filter),
            # opensuse site: leaps
            rpm.SUSERpmMirror('http://download.opensuse.org/distribution/leap/', 'repo/oss/', arch),
            # opensuse Kernel repo - common
            rpm.SUSERpmMirror('https://download.opensuse.org/repositories/Kernel:/', 'Backport/standard/', arch),
        ]

        # other arch's are stored differently on SUSE's site
        # in general, the /repositories/Kernel:/ are stored differently and require a filter
        if arch == 'x86_64':
            mirrors.append(rpm.SUSERpmMirror('https://download.opensuse.org/repositories/Kernel:/', 'Submit/standard/', arch))
            mirrors.append(rpm.SUSERpmMirror('https://download.opensuse.org/repositories/Kernel:/', 'standard/', arch))
        else:
            mirrors.append(rpm.SUSERpmMirror('https://download.opensuse.org/repositories/Kernel:/', 'Submit/ports/', arch))
            mirrors.append(rpm.SUSERpmMirror('https://download.opensuse.org/repositories/Kernel:/', 'ports/', arch))
            mirrors.append(rpm.SUSERpmMirror('https://download.opensuse.org/repositories/Kernel:/', 'ARM/', arch))
            mirrors.append(rpm.SUSERpmMirror('https://download.opensuse.org/repositories/Kernel:/', 'Backport/ports/', arch)),

        super(OpenSUSEMirror, self).__init__(mirrors, arch)


    def to_driverkit_config(self, release, deps):

        # matches driverkit target cli option
        target = 'opensuse'

        # dict for storing list of 
        dk_configs = {}

        # loop over deps for a given release and append
        for dep in deps:
            val = dk_configs.get(target)
            if not val:
                headers = [dep]
                dk_configs[target] = repo.DriverKitConfig(release, target, headers)
            else:
                val.headers.append(dep)
                dk_configs[target] = val

        return dk_configs.values()
