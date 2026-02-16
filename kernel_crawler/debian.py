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
from . import deb
import click
import sys

def repo_filter(dist):
    return 'stable' not in dist and 'testing' not in dist and not dist.startswith('Debian')

def fixup_deb_arch(arch):
    if arch == 'x86_64':
        return 'amd64'
    elif arch == 'aarch64':
        return 'arm64'

class DebianMirror(repo.Distro):
    def __init__(self, arch):
        arch = fixup_deb_arch(arch)
        mirrors = [
            deb.DebMirror('http://mirrors.edge.kernel.org/debian/', arch, repo_filter),
            deb.DebMirror('http://security.debian.org/', arch, repo_filter),
            deb.DebMirror('http://archive.raspberrypi.com/debian/', arch, repo_filter),
            deb.DebMirror('http://security.debian.org/debian-security/', arch, repo_filter),
            deb.DebMirror('http://archive.debian.org/debian/', arch, repo_filter),
           
        
        ]
        super(DebianMirror, self).__init__(mirrors, arch)

    # For Debian mirrors, we need to override this method so that dependencies
    # can be resolved (i.e. build_package_tree) across multiple repositories.
    # This is namely required for the linux-kbuild package, which is typically
    # hosted on a different repository compared to the kernel packages
    def get_package_tree(self, version=''):
        all_packages = {}
        all_kernel_packages = []
        packages = {}
        repos = self.list_repos()
        with click.progressbar(repos, label='Listing packages', file=sys.stderr, item_show_func=repo.to_s) as repos:
            for repository in repos:
                repo_packages = repository.get_raw_package_db()
                all_packages.update(repo_packages)
                kernel_packages = repository.get_package_list(repo_packages, version)
                all_kernel_packages.extend(kernel_packages)

        for release, dependencies in deb.DebRepository.build_package_tree(all_packages, all_kernel_packages).items():
            packages.setdefault(release, set()).update(dependencies)
        return packages

    def to_driverkit_config(self, release, deps):
        headers = []
        headers_rt = []
        headers_cloud = []
        headers_rpi = []
        # Magic to obtain `rt`, `cloud`, `rpi` and normal headers:
        # List is like this one:
        # "http://security.debian.org/pool/updates/main/l/linux/linux-headers-4.19.0-23-common_4.19.269-1_all.deb",
        # "http://security.debian.org/pool/updates/main/l/linux/linux-headers-4.19.0-23-rt-amd64_4.19.269-1_amd64.deb",
        # "http://security.debian.org/pool/updates/main/l/linux/linux-headers-4.19.0-23-common-rt_4.19.269-1_all.deb",
        # "http://security.debian.org/pool/updates/main/l/linux/linux-kbuild-4.19_4.19.282-1_amd64.deb",
        # "http://security.debian.org/pool/updates/main/l/linux/linux-headers-4.19.0-23-cloud-amd64_4.19.269-1_amd64.deb",
        # "http://security.debian.org/pool/updates/main/l/linux/linux-headers-4.19.0-23-amd64_4.19.269-1_amd64.deb"
        # So:
        # * common is split in `common-rt`, `common-rpi` and `common` (for cloud and normal)
        # * kbuild is the same across all flavors
        # * headers are split between `rt`, `cloud` and normal
        for dep in deps:
            if dep.find("headers") != -1:
                if dep.find("common") != -1:
                    if dep.find("-rt") != -1:
                        headers_rt.append(dep)
                    elif dep.find("-rpi") != -1:
                        headers_rpi.append(dep)
                    else:
                        headers.append(dep)
                        headers_cloud.append(dep)
                else:
                    if dep.find("-rt") != -1:
                        headers_rt.append(dep)
                    elif dep.find("-cloud") != -1:
                        headers_cloud.append(dep)
                    elif dep.find("-rpi") != -1:
                        headers_rpi.append(dep)
                    else:
                        headers.append(dep)
            if dep.find("kbuild") != -1:
                headers.append(dep)
                headers_rt.append(dep)
                headers_cloud.append(dep)
                headers_rpi.append(dep)

        final = []
        if len(headers) >= 3:
            final.append(repo.DriverKitConfig(release + "-" + self.arch, "debian", headers))
        if len(headers_rt) >= 3:
            final.append(repo.DriverKitConfig(release + "-rt-" + self.arch, "debian", headers_rt))
        if len(headers_cloud) >= 3:
            final.append(repo.DriverKitConfig(release + "-cloud-" + self.arch, "debian", headers_cloud))
        if len(headers_rpi) >= 3:
            final.append(repo.DriverKitConfig(release + "-rpi-" + self.arch, "debian", headers_rpi))
        return final
