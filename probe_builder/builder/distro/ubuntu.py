import logging
import os
import re

import click

from probe_builder.builder import toolkit
from .base_builder import DistroBuilder

logger = logging.getLogger(__name__)


class UbuntuBuilder(DistroBuilder):
    KERNEL_VERSION_RE = re.compile(r'(?P<version>[0-9]\.[0-9]+\.[0-9]+-[0-9]+)\.(?P<update>[0-9][^_]*)')
    KERNEL_RELEASE_RE = re.compile(r'(?P<release>[0-9]\.[0-9]+\.[0-9]+-[0-9]+-[a-z0-9-]+)')

    def unpack_kernels(self, workspace, distro, kernels):
        kernel_dirs = list()
        for release, debs in kernels:
            # we don't have the version handy, so gather it from all the package
            # names in the release. these all should match but at this point we can
            # only validate that it is so
            version = None

            for deb in debs:
                deb_basename = os.path.basename(deb)
                m = self.KERNEL_VERSION_RE.search(deb_basename)
                if not m:
                    raise ValueError("{} doesn't look like a kernel package".format(deb))
                if version is None:
                    version = (m.group('version'), m.group('update'))
                else:
                    new_version = (m.group('version'), m.group('update'))
                    if version != new_version:
                        raise ValueError("Unexpected version {}/{} from package {} (expected {}/{})".format(
                            new_version[0], new_version[1], deb,
                            version[0], version[1]
                        ))

            target = workspace.subdir('build', distro, version[0], version[1])
            kernel_dirs.append((release, target))

            for deb in debs:
                deb_basename = os.path.basename(deb)
                marker = os.path.join(target, '.' + deb_basename)
                toolkit.unpack_deb(workspace, deb, target, marker)

        return kernel_dirs

    def hash_config(self, release, target):
        return self.md5sum(os.path.join(target, 'boot/config-{}'.format(release)))

    def get_kernel_dir(self, workspace, release, target):
        return workspace.subdir(target, 'usr/src/linux-headers-{}'.format(release))

    def batch_packages(self, kernel_files):
        kernels = []

        # ubuntu kernels have two separate versions
        # e.g. the package linux-headers-5.4.0-86-generic_5.4.0-86.97_amd64.deb
        # has a "version" (used in the target dir) of 5.4.0-86/97
        # and a "release" (describing the paths inside the archive) of 5.4.0-86-generic
        #
        # sadly, it's not as straightforward as we'd wish. there's also a package
        # linux-headers-5.4.0-86_5.4.0-86.97_all.deb which is a dependency (potentially)
        # shared between multiple packages.
        #
        # so we need to unpack the debs into the "version" directory and then can end
        # up with multiple kernels in that directory. this means we can't return
        # a dict, but a list of tuples

        version_to_releases = dict()
        releases = dict()
        version_files = dict()

        for deb in kernel_files:
            deb_basename = os.path.basename(deb)

            # linux-headers-5.4.0-1063-azure-cvm_|5.4.0-1063.66+cvm3|_amd64.deb
            m = self.KERNEL_VERSION_RE.search(deb_basename)
            if not m:
                click.echo("Filename {} doesn't look like a kernel package (no version)".format(deb), err=True)
                continue
            version = m.group('version')
            update = m.group('update')
            version = '{}/{}'.format(version, update)


            # linux-headers-|5.4.0-1063-azure-cvm|_5.4.0-1063.66+cvm3_amd64.deb
            m = self.KERNEL_RELEASE_RE.search(deb_basename)
            if m:
                release = m.group('release')
                version_to_releases.setdefault(version, set()).add(release)
                releases.setdefault((release, version), []).append(deb)
            else:
                version_files.setdefault(version, []).append(deb)

        for version, release_ids in version_to_releases.items():
            for release_id in release_ids:
                release_files = releases[(release_id, version)]
                # add all the shared files that end up in the same directory
                release_files.extend(version_files.get(version, []))
                kernels.append((release_id, release_files))

        return kernels
