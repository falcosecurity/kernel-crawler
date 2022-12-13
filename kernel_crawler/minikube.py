import sys

from click import progressbar as ProgressBar
from semantic_version import Version as SemVersion

from .git import GitMirror


class MinikubeMirror(GitMirror):
    def __init__(self, arch):
        super(MinikubeMirror, self).__init__("kubernetes", "minikube", arch)
    
    def get_kernel_config_file_name(self, minikube_version):
        if SemVersion(minikube_version) >= SemVersion("1.26.0"):
            return "linux_" + self.arch + "_defconfig"
        return "linux_defconfig"
    
    def get_minikube_config_file_name(self, minikube_version):
        if SemVersion(minikube_version) >= SemVersion("1.26.0"):
            return "minikube_" + self.arch + "_defconfig"
        return "minikube_defconfig"

    def get_package_tree(self, version=''):
        self.list_repo()
        sys.stdout.flush()
        kernel_configs = {}
        minikube_versions = self.getVersions(3)
        
        for v in minikube_versions:
            bar = ProgressBar(label="Building config for minikube v{}".format(v), length=1, file=sys.stderr)
            # minikube has support for aarch64 starting from version 1.26.0.
            # versions older than 1.26.0 are just skipped if building for aarch64.
            if self.arch == "aarch64" and SemVersion(v) < SemVersion("1.26.0"):
                continue
            self.checkout_version(v)
            # same meaning as the output of "uname -r"
            kernel_release = self.extract_value(self.get_minikube_config_file_name(v),
                                                "BR2_LINUX_KERNEL_CUSTOM_VERSION_VALUE", "=")
            # kernelversion is computed as "1_" + minikube version.
            # The reason behind that is due to how minikube distributes the iso images.
            # It could happen that two different minikube versions use the same kernel release but
            # built with a different defconfig file. So having the minikube version in the kernelversion
            # makes easier to get the right falco drivers from within a minikube instance.
            # same meaning as "uname -v"
            kernel_version = "1_" + v
            defconfig_base64 = self.encode_base64_defconfig(self.get_kernel_config_file_name(v))
            kernel_configs[v] = {
                self.KERNEL_VERSION: kernel_version, 
                self.KERNEL_RELEASE: kernel_release,
                self.DISTRO_TARGET: "minikube",
                self.BASE_64_CONFIG_DATA: defconfig_base64,
                }
            bar.update(1)
            bar.render_finish()
        
        self.cleanup_repo()
        return kernel_configs
