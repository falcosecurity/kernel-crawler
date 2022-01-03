from collections import namedtuple
import os


class Context(object):
    pass


class Workspace(
    namedtuple(
        'Workspace', 'is_privileged mount_mapping workspace builder_source image_prefix')):

    def host_dir(self, container_dir):
        if self.mount_mapping is None:
            return container_dir
        for (container_mount, host_mount) in self.mount_mapping:
            if container_dir == container_mount:
                return host_mount
            elif container_dir.startswith(container_mount + '/'):
                return container_dir.replace(container_mount, host_mount)

    def in_docker(self):
        return self.mount_mapping is not None

    def host_workspace(self):
        return self.host_dir(self.workspace)

    def subdir(self, *args):
        return os.path.join(self.workspace, *args)


class Probe(namedtuple('Probe', 'sysdig_dir probe_name probe_version probe_device_name')):
    pass


class DownloadConfig(namedtuple('DownloadConfig', 'concurrency timeout retries extra_headers')):

    @staticmethod
    def default():
        return DownloadConfig(1, None, 1, None)
