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

import os
import base64

import requests
from lxml import html

from . import repo
from .repo import Repository, Distro
from .debian import fixup_deb_arch

class FlatcarRepository(Repository):
    def __init__(self, base_url):
        self.base_url = base_url

    def get_package_tree(self, version=''):
        release = os.path.basename(self.base_url.rstrip('/'))
        if version not in release:
            return {}
        defconfig = os.path.join(self.base_url, 'flatcar_production_image_kernel_config.txt')
        defconfig_base64 = base64.b64encode(requests.get(defconfig).content).decode()
        return {release: [defconfig_base64]}

    def __str__(self):
        return self.base_url


class FlatcarMirror(Distro):
    CHANNELS = ['stable', 'beta', 'alpha']

    def __init__(self, arch):
        arch = fixup_deb_arch(arch)
        mirrors = ['https://{c}.release.flatcar-linux.net/{a}-usr/'.format(c=channel, a=arch) for channel in self.CHANNELS]
        super(FlatcarMirror, self).__init__(mirrors, arch)

    def scan_repo(self, base_url):
        try:
            dists = requests.get(base_url)
            dists.raise_for_status()
        except requests.exceptions.RequestException:
            return {}
        dists = dists.content
        doc = html.fromstring(dists, base_url)
        dists = doc.xpath('/html/body//a[not(@href="../")]/@href')
        return [FlatcarRepository('{}{}'.format(base_url, dist.lstrip('./'))) for dist in dists
                if dist.endswith('/')
                and dist.startswith('./')
                and 'current' not in dist
                and '-' not in dist
                ]

    def list_repos(self):
        repos = []
        for repo in self.mirrors:
            repos.extend(self.scan_repo(repo))
        return repos

    def to_driverkit_config(self, release, deps):
        return repo.DriverKitConfig(release, "flatcar", None, "1", list(deps)[0])
