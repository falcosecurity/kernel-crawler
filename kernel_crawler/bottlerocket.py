import shutil
import sys

from click import progressbar as ProgressBar

from .git import GitMirror


class BottleRocketMirror(GitMirror):
    supported_kernel_releases = ["5.10", "5.15"]

    def __init__(self, arch):
        super(BottleRocketMirror, self).__init__("bottlerocket-os", "bottlerocket", arch)

    def get_kernel_config_file_name(self):
        return "config-bottlerocket"

    def get_bottlerocket_kernel_spec(self, kver):
        return "kernel-" + kver + ".spec"

    def get_package_tree(self, version=''):
        repo = self.list_repos()
        sys.stdout.flush()
        kernel_configs = {}
        bottlerocket_versions = self.getVersions(repo, 3)

        for v in bottlerocket_versions:
            bar = ProgressBar(label="Building config for bottlerocket v{}".format(v), length=1, file=sys.stderr)
            self.checkout_version(v, repo)
            # same meaning as the output of "uname -r"
            for kver in self.supported_kernel_releases:
                kernel_release = self.extract_kernel_release(v, repo, self.get_bottlerocket_kernel_spec(kver))
                kernel_version = "1_" + v
                defconfig_base64 = self.encode_base64_defconfig(v, repo, self.get_kernel_config_file_name())
                kernel_configs[v + "_" + kver] = {
                    self.KERNEL_VERSION: kernel_version,
                    self.KERNEL_RELEASE: kernel_release,
                    self.DISTRO_TARGET: "bottlerocket",
                    self.BASE_64_CONFIG_DATA: defconfig_base64,
                }
            bar.update(1)
            bar.render_finish()

        shutil.rmtree(repo.workdir, True)
        return kernel_configs
