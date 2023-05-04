import sys

from click import progressbar as ProgressBar
from semantic_version import Version as SemVersion

from .git import GitMirror

from .debian import fixup_deb_arch

class TalosMirror(GitMirror):
    def __init__(self, arch):
        super(TalosMirror, self).__init__("siderolabs", "pkgs", fixup_deb_arch(arch))

    def get_package_tree(self, version=''):
        self.list_repo()
        sys.stdout.flush()
        kernel_configs = {}
        talos_versions = self.getVersions(3)
        
        for v in talos_versions:
            bar = ProgressBar(label="Building config for talos v{}".format(v), length=1, file=sys.stderr)
            self.checkout_version(v)
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
            kernel_version = "1_" + v
            defconfig_base64 = self.encode_base64_defconfig("config-" + self.arch)
            kernel_configs[v] = {
                self.KERNEL_VERSION: kernel_version, 
                self.KERNEL_RELEASE: kernel_release,
                self.DISTRO_TARGET: "talos",
                self.BASE_64_CONFIG_DATA: defconfig_base64,
                }
            bar.update(1)
            bar.render_finish()
        
        self.cleanup_repo()
        return kernel_configs
