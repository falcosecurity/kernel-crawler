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

from . import rpm
from . import repo

class PhotonOsRepository(rpm.RpmRepository):
    @classmethod
    def kernel_package_query(cls):
        # We exclude `esx` kernels because they don't support CONFIG_TRACEPOINTS,
        # see https://github.com/vmware/photon/issues/1223.
        return '''((name = 'linux' OR name LIKE 'linux-%devel%') AND name NOT LIKE '%esx%' AND name NOT LIKE '%PAM%')'''


class PhotonOsMirror(repo.Distro):
    PHOTON_OS_VERSIONS = [
        ('3.0', ''),
        ('3.0', '_release'),
        ('3.0', '_updates'),
        ('4.0', ''),
        ('4.0', '_release'),
        ('4.0', '_updates'),
        ('5.0', ''),
        ('5.0', '_release'),
        ('5.0', '_updates'),
    ]

    def __init__(self, arch):
        super(PhotonOsMirror, self).__init__([], arch)

    def list_repos(self):
        return [
            PhotonOsRepository('https://packages.vmware.com/photon/{v}/photon{r}_{v}_{a}/'.format(
                v=version, r=repo_tag, a=self.arch))
            for version, repo_tag in self.PHOTON_OS_VERSIONS]

    def to_driverkit_config(self, release, deps):
        # PhotonOS kernel packages have a ".$arch" suffix, 
        # thus our kernelrelease is different from `uname -r` output.
        # Fix this by manually removing the suffix.
        suffix = "."+self.arch
        if release.endswith(suffix):
            release = release[:-len(suffix)]
        for dep in deps:
            if dep.find("-devel") != -1:
                return repo.DriverKitConfig(release, "photon", dep)
