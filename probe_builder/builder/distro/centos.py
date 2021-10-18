import logging
import os
import re

import click

from probe_builder.builder import toolkit
from .base_builder import DistroBuilder

logger = logging.getLogger(__name__)


class CentosBuilder(DistroBuilder):
    RPM_KERNEL_RELEASE_RE = re.compile(r'^kernel-(uek-)?(core-|devel-|modules-)?(?P<release>.*)\.rpm$')

    def unpack_kernels(self, workspace, distro, kernels):
        kernel_dirs = dict()

        for release, rpms in kernels.items():
            target = workspace.subdir('build', distro, release)
            kernel_dirs[release] = target

            for rpm in rpms:
                rpm_basename = os.path.basename(rpm)
                marker = os.path.join(target, '.' + rpm_basename)
                toolkit.unpack_rpm(workspace, rpm, target, marker)

        return kernel_dirs

    def hash_config(self, release, target):
        try:
            return self.md5sum(os.path.join(target, 'boot/config-{}'.format(release)))
        except IOError:
            return self.md5sum(os.path.join(target, 'lib/modules/{}/config'.format(release)))

    def get_kernel_dir(self, workspace, release, target):
        return workspace.subdir(target, 'usr/src/kernels', release)

    def batch_packages(self, kernel_files):
        kernels = dict()
        for rpm in kernel_files:
            rpm_filename = os.path.basename(rpm)
            m = self.RPM_KERNEL_RELEASE_RE.match(rpm_filename)
            if not m:
                click.echo("Filename {} doesn't look like a kernel package".format(rpm_filename), err=True)
                continue
            kernels.setdefault(m.group('release'), []).append(rpm)

        return kernels
