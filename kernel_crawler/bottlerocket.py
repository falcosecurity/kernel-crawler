import base64
import os
import sys

import requests
import rpmfile
from click import progressbar as ProgressBar

from .git import GitMirror


class BottleRocketMirror(GitMirror):
    supported_kernel_releases = ["5.10", "5.15"]
    supported_flavors = ["aws", "metal", "vmware"]

    def __init__(self, arch):
        super(BottleRocketMirror, self).__init__("bottlerocket-os", "bottlerocket", arch)

    def get_kernel_config_file_name(self, flavor=''):
        return "config-bottlerocket"+flavor

    def get_bottlerocket_kernel_spec(self, kver):
        return "kernel-" + kver + ".spec"

    def fetch_base_config(self, kver):
        source = self.extract_value(self.get_bottlerocket_kernel_spec(kver), "Source0", ":")
        if source is None:
            return None

        alkernel = requests.get(source)
        alkernel.raise_for_status()
        with open('/tmp/alkernel.rpm', 'wb') as f:
            f.write(alkernel.content)

        with rpmfile.open('/tmp/alkernel.rpm') as rpm:
            # Extract a fileobject from the archive
            fd = rpm.extractfile('config-' + self.arch)
            baseconfig = [line for line in fd.readlines()]

        os.remove('/tmp/alkernel.rpm')
        return baseconfig

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
            for kver in self.supported_kernel_releases:
                # same meaning as the output of "uname -r"
                kernel_release = self.extract_value(self.get_bottlerocket_kernel_spec(kver), "Version", ":")
                if kernel_release is None:
                    continue

                # Load base config
                baseconfig = self.fetch_base_config(kver)
                if baseconfig is None:
                    continue

                # Load common config
                commonconfig_file = self.search_file(self.get_kernel_config_file_name())
                if commonconfig_file is None:
                    continue

                with open(commonconfig_file, 'r') as fd:
                    commonconfig = fd.readlines()

                for flavor in self.supported_flavors:
                    flavorconfig_file = self.search_file(self.get_kernel_config_file_name("-" + flavor))
                    if flavorconfig_file is None:
                        continue

                    # Load flavor specific config
                    with open(flavorconfig_file, 'r') as fd:
                        flavorconfig = fd.readlines()

                    # Merge flavor and common config
                    flavorconfig += commonconfig

                    # Finally, patch baseconfig with flavor config
                    finalconfig = self.patch_config(baseconfig, flavorconfig)

                    kernel_version = "1_" + v + "-" + flavor
                    defconfig_base64 = base64.b64encode(b''.join(finalconfig)).decode()
                    kernel_configs[v + "_" + kver] = {
                        self.KERNEL_VERSION: kernel_version,
                        self.KERNEL_RELEASE: kernel_release,
                        self.DISTRO_TARGET: "bottlerocket",
                        self.BASE_64_CONFIG_DATA: defconfig_base64,
                    }

            bar.update(1)
            bar.render_finish()

        self.cleanup_repo()
        return kernel_configs
