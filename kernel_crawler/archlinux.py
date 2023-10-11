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

from bs4 import BeautifulSoup
import re

from kernel_crawler.utils.download import get_url
from . import repo

class ArchLinuxRepository(repo.Repository):

    _linux_headers_pattern = 'linux.*headers-'
    _package_suffix_pattern = '.pkg.tar.*'

    def __init__(self, base_url, arch):
        self.base_url = base_url
        self.arch = arch

    def __str__(self):
        return self.base_url

    def parse_kernel_release(self, kernel_package):

        # trim off 'linux*headers'
        trimmed = re.sub(self._linux_headers_pattern, '', kernel_package)
        # trim off the '.pkg.tar.*'
        version_with_arch = re.sub(self._package_suffix_pattern, '', trimmed)

        # trim off the architecture
        version = re.sub(f'-{self.arch}', '', version_with_arch)

        return version

    def get_package_tree(self, filter=''):
        packages = {}

        soup = BeautifulSoup(get_url(self.base_url), features='lxml')
        for a in soup.find_all('a', href=True):
            package = a['href']
            # skip .sig and .. links
            if not package.endswith('.sig') and package != '../':
                parsed_kernel_release = self.parse_kernel_release(package)

                packages.setdefault(parsed_kernel_release, set()).add(self.base_url + package)

        return packages


class ArchLinuxMirror(repo.Distro):

    _base_urls = []

    def __init__(self, arch):

        if arch == 'x86_64':
            self._base_urls.append('https://archive.archlinux.org/packages/l/linux-headers/')                 # stable
            self._base_urls.append('https://archive.archlinux.org/packages/l/linux-hardened-headers/')        # hardened
            self._base_urls.append('https://archive.archlinux.org/packages/l/linux-lts-headers/')             # lts
            self._base_urls.append('https://archive.archlinux.org/packages/l/linux-zen-headers/')             # zen
        elif arch == 'aarch64':
            self._base_urls.append('http://tardis.tiny-vps.com/aarm/packages/l/linux-aarch64-headers/')       # arm 64-bit
        else:  # can be implemented later
            self._base_urls.append('http://tardis.tiny-vps.com/aarm/packages/l/linux-armv5-headers/')         # arm v5
            self._base_urls.append('http://tardis.tiny-vps.com/aarm/packages/l/linux-armv7-headers/')         # arm v7
            self._base_urls.append('http://tardis.tiny-vps.com/aarm/packages/l/linux-raspberrypi4-headers/')  # rpi4
            self._base_urls.append('http://tardis.tiny-vps.com/aarm/packages/l/linux-raspberrypi-headers/')   # other rpi

        super(ArchLinuxMirror, self).__init__(self._base_urls, arch)


    def list_repos(self):
        mirrors = []

        for mirror in self._base_urls:
            mirrors.append(ArchLinuxRepository(mirror, self.arch))

        return mirrors


    def to_driverkit_config(self, release, deps):
        for dep in deps:
            return repo.DriverKitConfig(release, "arch", dep)
