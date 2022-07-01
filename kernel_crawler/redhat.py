from . import repo
from .container import Container
import re

class RedhatContainer(repo.ContainerDistro):
    def __init__(self, images):
        super(RedhatContainer, self).__init__(images)

    def get_kernel_versions(self):
        kernels = {}
        for image in self.images:
            c = Container(image)
            cmd_out = c.run_cmd("repoquery --show-duplicates kernel-devel")
            for log_line in cmd_out:
                m = re.search("(?<=kernel-devel-0:).*", log_line);
                if m:
                    kernels[m.group(0)] = []
        return kernels

    def to_driverkit_config(self, release, deps):
        return repo.DriverKitConfig(release, "redhat", list(deps))
