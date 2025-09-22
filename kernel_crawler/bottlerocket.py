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

import base64
import os
import re
import sys

import requests
import rpmfile
from click import progressbar as ProgressBar

from .git import GitMirror


class BottleRocketMirror(GitMirror):
    def __init__(self, arch):
        super(BottleRocketMirror, self).__init__("bottlerocket-os", "bottlerocket", arch)

    def fetch_base_config(self, kverspec):
        source = self.extract_value(kverspec, "Source0", ":")
        if source is None:
            return None

        alkernel = requests.get(source, timeout = 15)
        alkernel.raise_for_status()
        with open('/tmp/alkernel.rpm', 'wb') as f:
            f.write(alkernel.content)

        with rpmfile.open('/tmp/alkernel.rpm') as rpm:
            # Extract a fileobject from the archive
            fd = rpm.extractfile('config-' + self.arch)
            baseconfig = [line for line in fd.readlines()]

        os.remove('/tmp/alkernel.rpm')
        return baseconfig

    def extract_flavor(self, flavorconfig_path):
        flavorconfig_file = os.path.basename(flavorconfig_path)
        return re.match(r"^config-bottlerocket-(.*)", flavorconfig_file).group(1)

    def extract_kver(self, kverspec_file):
        return re.match(r"^kernel-(.*).spec$", kverspec_file).group(1)

    def set_kernel_config(self, baseconfig, key, value):
        for i, line in enumerate(baseconfig):
            if key in str(line):
                baseconfig[i] = key.encode() + b'=' + value.encode()
                break

    def unset_kernel_config(self, baseconfig, key):
        for i, line in enumerate(baseconfig):
            if line.startswith(key):
                baseconfig[i] = b'# ' + key.encode() + b' is not set\n'
                break

    def patch_config(self, baseconfig, patch):
        for line in patch:
            if line.startswith("#"):
                continue
            vals = line.split("=", 1)
            if len(vals) != 2:
                continue
            key = vals[0]
            value = vals[1]
            if value == "n":
                self.unset_kernel_config(baseconfig, key)
            else:
                self.set_kernel_config(baseconfig, key, value)
        return baseconfig

    def get_package_tree(self, version=''):
        self.list_repo()
        sys.stdout.flush()
        kernel_configs = {}
        bottlerocket_versions = self.getVersions(3)

        for v in bottlerocket_versions:
            bar = ProgressBar(label="Building config for bottlerocket v{}".format(v), length=1, file=sys.stderr)
            self.checkout_version(v)

            # Find supported kernels dynamically
            supported_kernel_specs = self.match_file("kernel-.*.spec", True)
            for kverspec_file in supported_kernel_specs:
                name = os.path.basename(kverspec_file)
                wd = os.path.dirname(kverspec_file)
                kver = self.extract_kver(name)

                # same meaning as the output of "uname -r"
                kernel_release = self.extract_value(kverspec_file, "Version", ":")
                if kernel_release is None:
                    continue

                # Load base config
                vanillaconfig = self.fetch_base_config(kverspec_file)
                if vanillaconfig is None:
                    continue

                # Load common config
                specific_config_file = self.search_file("config-bottlerocket", wd)
                if specific_config_file is None:
                    continue

                with open(specific_config_file, 'r') as fd:
                    specific_config = fd.readlines()

                # Find supported flavors dynamically
                supported_flavors = self.match_file("config-bottlerocket-.*", True, wd)
                if supported_flavors:
                    for flavorconfig_file in supported_flavors:
                        flavor = self.extract_flavor(flavorconfig_file)

                        # Load flavor specific config
                        with open(flavorconfig_file, 'r') as fd:
                            flavorconfig = fd.readlines()

                        # Merge flavor and common config
                        flavorconfig += specific_config

                        # Finally, patch baseconfig with flavor config
                        finalconfig = self.patch_config(vanillaconfig, flavorconfig)
                        defconfig_base64 = base64.b64encode(b''.join(finalconfig)).decode()

                        kernel_version = "1_" + v + "-" + flavor

                        # Unique key
                        kernel_configs[v + "_" + kver + "-" + flavor] = {
                            self.KERNEL_VERSION: kernel_version,
                            self.KERNEL_RELEASE: kernel_release,
                            self.DISTRO_TARGET: "bottlerocket",
                            self.BASE_64_CONFIG_DATA: defconfig_base64,
                        }
                else:
                    # NOTE: to keep backward compatibility with existing drivers
                    # and driver loader logic, push these kernels for each flavor
                    # even if the config is the same among all of them.
                    # We will build 3x the drivers but we will be backward compatible.
                    for flavor in ['aws','metal','vmware']:
                        finalconfig = self.patch_config(vanillaconfig, specific_config)
                        defconfig_base64 = base64.b64encode(b''.join(finalconfig)).decode()

                        kernel_version = "1_" + v + "-" + flavor

                        # Unique key
                        kernel_configs[v + "_" + kver + "-" + flavor] = {
                            self.KERNEL_VERSION: kernel_version,
                            self.KERNEL_RELEASE: kernel_release,
                            self.DISTRO_TARGET: "bottlerocket",
                            self.BASE_64_CONFIG_DATA: defconfig_base64,
                        }

            bar.update(1)
            bar.render_finish()

        self.cleanup_repo()
        return kernel_configs
