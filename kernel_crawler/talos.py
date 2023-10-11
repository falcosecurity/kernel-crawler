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

import sys
import tempfile
import pygit2

from click import progressbar as ProgressBar
from semantic_version import Version as SemVersion

from .git import GitMirror,ProgressCallback

from .debian import fixup_deb_arch

class TalosMirror(GitMirror):
    def __init__(self, arch):
        self.backup_repo = None
        self.pkgs_repo = None
        super(TalosMirror, self).__init__("siderolabs", "talos", fixup_deb_arch(arch))

    def get_package_tree(self, version=''):
        self.list_repo()
        sys.stdout.flush()
        kernel_configs = {}
        talos_versions = self.getVersions(3)
        
        # Clone pkgs repo
        work_dir = tempfile.mkdtemp(prefix="pkgs-")
        self.pkgs_repo = pygit2.clone_repository("https://github.com/siderolabs/pkgs.git", work_dir, callbacks=ProgressCallback("pkgs"))
        
        # Store "talos" repo as we switch to use "pkgs" repo
        self.backup_repo = self.repo
        
        for v in talos_versions:
            # Use correct repo
            self.repo = self.backup_repo
            bar = ProgressBar(label="Building config for talos v{}".format(v), length=1, file=sys.stderr)
            
            self.checkout_version(v)
                        
            # Fetch "pkgs" repo hash
            pkgs_ver = self.extract_line("pkg/machinery/gendata/data/pkgs")
            if pkgs_ver is None:
                continue
            
            sempkgs_ver = SemVersion(pkgs_ver[1:])
            
            # Extract the commit hash if needed, else just use the tag name (eg: v1.4.0)
            # Note: full tag is like: v1.5.0-alpha.0-15-g813b3c3 or v1.5.0
            # so, pkgs_ver will be the string without "v".
            # In the end, in case of hash, the prerelease will be "alpha.0-15-g813b3c3";
            # find "-g" and take the hash.
            if sempkgs_ver.prerelease:
                pkgs_ver = sempkgs_ver.prerelease[0].split("-g", 1)[1]       
            
            # Use "pkgs" repo
            self.repo = self.pkgs_repo
            
            # Checkout required hash
            self.checkout_hash(pkgs_ver)
            
            # same meaning as the output of "uname -r"
            kernel_release = self.extract_value("Pkgfile", "linux_version", ":")
            # Skip when we cannot load a kernel_release
            if kernel_release is None:
                continue
                    
            # kernelversion is computed as "1_" + talos version.
            # The reason behind that is due to how talos distributes the iso images.
            # It could happen that two different talos versions use the same kernel release but
            # built with a different defconfig file. So having the talos version in the kernelversion
            # makes easier to get the right falco drivers from within a talos instance.
            # same meaning as "uname -v"
            kernel_version = "1_v" + v
            defconfig_base64 = self.encode_base64_defconfig("config-" + self.arch)
            kernel_configs[v] = {
                self.KERNEL_VERSION: kernel_version, 
                self.KERNEL_RELEASE: kernel_release + "-talos",
                self.DISTRO_TARGET: "talos",
                self.BASE_64_CONFIG_DATA: defconfig_base64,
                }
            bar.update(1)
            bar.render_finish()
        
        self.cleanup_repo()
        self.repo = self.pkgs_repo
        self.cleanup_repo()
        return kernel_configs
