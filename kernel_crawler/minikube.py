import tempfile
import shutil
import re
import os
import base64
import sys
from types import NoneType

from click import progressbar as ProgressBar
from semantic_version import Version as SemVersion
import pygit2

from .repo import Distro, DriverKitConfig


class ProgressCallback(pygit2.RemoteCallbacks):
    def __init__(self):
        self.progress_bar_initialized = False
        super().__init__()
    def transfer_progress(self, stats):
        if not self.progress_bar_initialized:
            bar = ProgressBar(label='Cloning minikube repository',length=stats.total_objects, file=sys.stderr)
        bar.update(stats.indexed_objects)
        if stats.indexed_objects == stats.total_objects:
            bar.render_finish()

class MinikubeMirror(Distro):
    # dictionary keys used to build the kernel configuration dict.
    KERNEL_VERSION = "kernelversion"
    KERNEL_RELEASE = "kernelrelease"
    DISTRO_TARGET = "target"
    BASE_64_CONFIG_DATA = "kernelconfigdata"

    def __init__(self, arch):
        mirrors = "https://github.com/kubernetes/minikube.git"
        
        Distro.__init__(self, mirrors, arch)
    
    def clone_repo(self, repo_url):
        work_dir = tempfile.mkdtemp(prefix="minikube-")
        return pygit2.clone_repository(repo_url, work_dir, callbacks=ProgressCallback())

    def list_repos(self):
        return self.clone_repo(self.mirrors)

    def getVersions(self, repo):
        re_tags = re.compile('^refs/tags/v(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$')
        
        all_versions = [os.path.basename(v).strip('v') for v in repo.references if re_tags.match(v)]
        all_versions.sort(key=SemVersion)

        no_patch_versions = list(filter((lambda x: SemVersion(x).patch == 0), all_versions))
        no_patch_versions.sort(key=SemVersion)
        
        # We only get the last three releases without considering the patch releases.
        no_patch_versions = no_patch_versions[-3:]
        # Here we are taking the three last releases plus the patch releases if they have any.
        # We are just taking all the releases(x.y.z) that are equal or greater than the older release we are considering,
        # i.e the older from the last three releases.
        # For example, if the last three releases without considering the patches are : 1.24.0, 1.25.0 and 1.26.0 then
        # we will consider the three release + all their patch releases.
        return [v for v in all_versions if SemVersion(v) >= SemVersion(no_patch_versions[0])]

    def checkout_version(self, minikube_version, repo):
        repo.checkout("refs/tags/v" + minikube_version)

    def search_files(self, directory, file_name):
        for dirpath, dirnames, files in os.walk(directory):
            for name in files :
                if name == file_name:
                    return os.path.join(dirpath, name)
        return NoneType
    
    def extract_kernel_release(self, minikube_version, repo):
        # here kernel release is the same a the one given by "uname -r"
        file_name = self.get_minikube_config_file_name(minikube_version)
        full_path = self.search_files(repo.workdir, file_name)
        for line in open(full_path):
            if re.search(r'^BR2_LINUX_KERNEL_CUSTOM_VERSION_VALUE=', line):                
                tokens = line.strip().split('=')
                return tokens[1].strip('"')
    
    def encode_base64_defconfig(self, minikube_version, repo):
        file_name = self.get_kernel_config_file_name(minikube_version)
        full_path = self.search_files(repo.workdir, file_name)
        with open(full_path, "rb") as config_file:
            return base64.b64encode(config_file.read()).decode()
    
    def get_kernel_config_file_name(self, minikube_version):
        if SemVersion(minikube_version) >= SemVersion("1.26.0"):
            return "linux_" + self.arch + "_defconfig"
        return "linux_defconfig"
    
    def get_minikube_config_file_name(self, minikube_version):
        if SemVersion(minikube_version) >= SemVersion("1.26.0"):
            return "minikube_" + self.arch + "_defconfig"
        return "minikube_defconfig"

    def get_package_tree(self, version=''):
        repo = self.list_repos()
        kernel_configs = {}
        minikube_versions = self.getVersions(repo)
        
        for v in minikube_versions:
            bar = ProgressBar(label="Building config for minikube v{}".format(v), length=1, file=sys.stderr)
            # minikube has support for aarch64 starting from version 1.26.0.
            # versions older than 1.26.0 are just skipped if building for aarch64.
            if self.arch == "aarch64" and SemVersion(v) < SemVersion("1.26.0"):
                continue
            self.checkout_version(v, repo)
            # same meaning as the output of "uname -r"
            kernel_release = self.extract_kernel_release(v, repo)
            # kernelversion is computed as "1_" + minikube version.
            # The reason behind that is due to how minikube distributes the iso images.
            # It could happen that two different minikube versions use the same kernel release but
            # built with a different defconfig file. So having the minikube version in the kernelversion
            # makes easier to get the right falco drivers from within a minikube instance.
            # same meaning as "uname -v"
            kernel_version = "1_" + v
            defconfig_base64 = self.encode_base64_defconfig(v, repo)
            kernel_configs[v] = {
                self.KERNEL_VERSION: kernel_version, 
                self.KERNEL_RELEASE: kernel_release,
                self.DISTRO_TARGET: "minikube",
                self.BASE_64_CONFIG_DATA: defconfig_base64,
                }
            bar.update(1)
            bar.render_finish()
        
        shutil.rmtree(repo.workdir, True)
        return kernel_configs

    def to_driverkit_config(self, distro_release, config):
        return DriverKitConfig(
            config[self.KERNEL_RELEASE],
            config[self.DISTRO_TARGET],
            None,
            config[self.KERNEL_VERSION],
            config[self.BASE_64_CONFIG_DATA])