import logging
import os
import re

import click

from probe_builder.builder import toolkit
from probe_builder.builder.distro.base_builder import DistroBuilder

logger = logging.getLogger(__name__)


class DebianBuilder(DistroBuilder):
    KERNEL_VERSION_RE = re.compile(r'(?P<version>[0-9]\.[0-9]+\.[0-9]+(-[^-]+)?)-(?P<arch>[a-z0-9]+)')
    KBUILD_PACKAGE_RE = re.compile(r'linux-kbuild-(?P<major>[0-9]\.[0-9]+)_')

    @staticmethod
    def _reparent_link(base_path, release, link_name):
        build_link_path = os.path.join(base_path, 'lib/modules', release, link_name)
        build_link_target = os.readlink(build_link_path)
        if build_link_target.startswith('/'):
            build_link_target = '../../..' + build_link_target
            os.unlink(build_link_path)
            os.symlink(build_link_target, build_link_path)

    def unpack_kernels(self, workspace, distro, kernels):
        kernel_dirs = dict()

        for release, debs in kernels.items():
            version, arch = release.rsplit('-', 1)

            target = workspace.subdir('build', distro, version)
            kernel_dirs[release] = target

            for deb in debs:
                deb_basename = os.path.basename(deb)
                marker = os.path.join(target, '.' + deb_basename)
                toolkit.unpack_deb(workspace, deb, target, marker)

        for release, target in kernel_dirs.items():
            kerneldir = self.get_kernel_dir(workspace, release, target)

            base_path = workspace.subdir(target)
            self._reparent_link(base_path, release, 'build')
            self._reparent_link(base_path, release, 'source')

            makefile = os.path.join(kerneldir, 'Makefile')
            makefile_orig = makefile + '.sysdig-orig'
            target_in_container = target.replace(workspace.workspace, '/build/probe')
            if not os.path.exists(makefile_orig):
                with open(makefile) as fp:
                    orig = fp.read()
                with open(makefile_orig, 'w') as fp:
                    fp.write(orig)
                patched = orig.replace('/usr/src', os.path.join(target_in_container, 'usr/src'))
                with open(makefile, 'w') as fp:
                    fp.write(patched)

        return kernel_dirs

    def hash_config(self, release, target):
        return self.md5sum(os.path.join(target, 'boot/config-{}'.format(release)))

    def get_kernel_dir(self, workspace, release, target):
        return workspace.subdir(target, 'usr/src/linux-headers-{}'.format(release))

    def batch_packages(self, kernel_files):
        kernels = dict()

        # similar to ubuntu, debian has two version numbers per (kernel) package
        # e.g. linux-headers-5.10.0-8-amd64_5.10.46-5_amd64.deb
        #
        # fortunately, we unpack to 5.10.0-8 and look for 5.10.0-8-amd64 inside
        # so we can easily find the requested directory name from the release
        # also, for every minor kernel version (like 5.10) there's a matching
        # kbuild-x.xx package that we need to include in the build directory

        common_packages = {}
        arch_packages = {}
        kbuild_packages = {}

        for deb in kernel_files:
            deb_basename = os.path.basename(deb)

            if 'linux-kbuild' in deb:
                m = self.KBUILD_PACKAGE_RE.search(deb_basename)
                if not m:
                    click.echo("Filename {} doesn't look like a kbuild package (no version)".format(deb), err=True)
                    continue
                kbuild_packages[m.group('major')] = deb
                continue

            m = self.KERNEL_VERSION_RE.search(deb_basename)
            if not m:
                click.echo("Filename {} doesn't look like a kernel package (no version)".format(deb), err=True)
                continue
            version = m.group('version')
            arch = m.group('arch')

            if arch == 'common':
                common_packages.setdefault(version, []).append(deb)
            else:
                arch_packages.setdefault(version, {}).setdefault(arch, []).append(deb)

        for version, per_arch in arch_packages.items():
            for arch, packages in per_arch.items():
                packages.extend(common_packages.get(version, []))
                major, minor, _ = version.split('.', 2)
                major_version = '{}.{}'.format(major, minor)
                kbuild_pkg = kbuild_packages.get(major_version)
                if kbuild_pkg:
                    packages.append(kbuild_pkg)
                kernels['{}-{}'.format(version, arch)] = packages

        return kernels
