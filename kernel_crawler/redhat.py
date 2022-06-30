from . import repo
import re

class RedhatContainer(repo.ContainerDistro):
    def __init__(self, image):
        super(RedhatContainer, self).__init__(image)

    def get_kernel_versions(self):
        kernels = {}
        cmd_out = super().run_cmd("repoquery --show-duplicates kernel-devel")
        for log_line in cmd_out:
            m = re.search("(?<=kernel-devel-0:).*", log_line);
            if m:
                kernels[m.group(0)] = []
        return kernels

    def to_driverkit_config(self, release, deps):
        return repo.DriverKitConfig(release, "redhat", list(deps))
