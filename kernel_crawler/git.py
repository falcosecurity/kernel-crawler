import tempfile
import shutil
import re
import os
import base64
import sys

from click import progressbar as ProgressBar
from semantic_version import Version as SemVersion
import pygit2

from kernel_crawler.repo import Distro, DriverKitConfig


class ProgressCallback(pygit2.RemoteCallbacks):
    def __init__(self, name):
        self.progress_bar_initialized = False
        self.bar = None
        self.name = name
        super().__init__()

    def transfer_progress(self, stats):
        if not self.progress_bar_initialized:
            self.bar = ProgressBar(label='Cloning ' + self.name + ' repository', length=stats.total_objects, file=sys.stderr)
            self.bar.update(1)
            self.progress_bar_initialized = True
        if not self.bar.is_hidden:
            self.bar.update(1, stats.indexed_objects)
        if stats.indexed_objects == stats.total_objects:
            self.bar.render_finish()


class GitMirror(Distro):
    # dictionary keys used to build the kernel configuration dict.
    KERNEL_VERSION = "kernelversion"
    KERNEL_RELEASE = "kernelrelease"
    DISTRO_TARGET = "target"
    BASE_64_CONFIG_DATA = "kernelconfigdata"

    def __init__(self, repoorg, reponame, arch):
        mirrors = "https://github.com/"+repoorg+"/"+reponame+".git"
        self.repo = None
        self.repo_name = reponame
        Distro.__init__(self, mirrors, arch)

    def clone_repo(self, repo_url):
        work_dir = tempfile.mkdtemp(prefix=self.repo_name + "-")
        return pygit2.clone_repository(repo_url, work_dir, callbacks=ProgressCallback(self.repo_name))

    def list_repo(self):
        self.repo = self.clone_repo(self.mirrors)

    def cleanup_repo(self):
        shutil.rmtree(self.repo.workdir, True)

    def getVersions(self, last_n=0):
        re_tags = re.compile('^refs/tags/v(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$')

        all_versions = [os.path.basename(v).strip('v') for v in self.repo.references if re_tags.match(v)]
        all_versions.sort(key=SemVersion)

        no_patch_versions = list(filter((lambda x: SemVersion(x).patch == 0), all_versions))
        no_patch_versions.sort(key=SemVersion)

        # We only get the lastN releases without considering the patch releases if requested
        if last_n > 0:
            no_patch_versions = no_patch_versions[-last_n:]

        # Here we are taking the three last releases plus the patch releases if they have any.
        # We are just taking all the releases(x.y.z) that are equal or greater than the older release we are considering,
        # i.e the older from the last three releases.
        return [v for v in all_versions if SemVersion(v) >= SemVersion(no_patch_versions[0])]

    def checkout_version(self, vers):
        self.repo.checkout("refs/tags/v" + vers)

    def search_file(self, file_name):
        for dirpath, dirnames, files in os.walk(self.repo.workdir):
            for name in files:
                if name == file_name:
                    return os.path.join(dirpath, name)
        return None

    def extract_value(self, file_name, key, sep):
        # here kernel release is the same as the one given by "uname -r"
        full_path = self.search_file(file_name)
        for line in open(full_path):
            if re.search(r'^'+key + sep, line):
                tokens = line.strip().split(sep, 1)
                return tokens[1].strip('"').strip()
        return None

    def encode_base64_defconfig(self, file_name):
        full_path = self.search_file(file_name)
        if full_path is None:
            return None
        with open(full_path, "rb") as config_file:
            return base64.b64encode(config_file.read()).decode()

    def to_driverkit_config(self, distro_release, config):
        return DriverKitConfig(
            config[self.KERNEL_RELEASE],
            config[self.DISTRO_TARGET],
            None,
            config[self.KERNEL_VERSION],
            config[self.BASE_64_CONFIG_DATA])