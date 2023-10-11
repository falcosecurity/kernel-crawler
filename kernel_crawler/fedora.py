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

from . import repo, rpm

def repo_filter(version):
    """Don't bother testing ancient versions"""
    try:
        return int(version.rstrip('/')) >= 32
    except ValueError:
        return False


class FedoraMirror(repo.Distro):
    def __init__(self, arch):
        mirrors = [
            rpm.RpmMirror('https://mirrors.kernel.org/fedora/releases/', 'Everything/' + arch + '/os/', repo_filter),
            rpm.RpmMirror('https://mirrors.kernel.org/fedora/updates/', 'Everything/' + arch + '/', repo_filter),
            rpm.RpmMirror('https://archives.fedoraproject.org/pub/archive/fedora/linux/releases/', 'Everything/' + arch + '/os/', repo_filter),
            rpm.RpmMirror('https://archives.fedoraproject.org/pub/archive/fedora/linux/updates/', 'Everything/' + arch + '/os/', repo_filter),
        ]
        super(FedoraMirror, self).__init__(mirrors, arch)

    def to_driverkit_config(self, release, deps):
        for dep in deps:
            if dep.find("devel") != -1:
                return repo.DriverKitConfig(release, "fedora", dep)
