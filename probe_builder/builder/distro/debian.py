import logging
import os
import re
import traceback
import pprint

import click

from probe_builder.builder import toolkit
from probe_builder.builder.distro.base_builder import DistroBuilder

logger = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(depth=4)

class DebianBuilder(DistroBuilder):
    KERNEL_VERSION_RE = re.compile(r'-(?P<version>[0-9]\.[0-9]+\.[0-9]+(-[^-]+)?)-(?P<vararch>[a-z0-9-]+)_')
    KBUILD_PACKAGE_RE = re.compile(r'linux-kbuild-(?P<major>[0-9]\.[0-9]+)_')


    def crawl(self, workspace, distro, crawler_distro, download_config=None, filter=''):
        # for debian, we essentially want to discard the classification work performed by the crawler,
        # and batch packages together

        # call the parent's method
        crawled_dict = super().crawl(workspace=workspace, distro=distro, crawler_distro=crawler_distro, download_config=download_config, filter=filter)

        # flatten that dictionary into a single list, retaining ONLY package urls and discarding the release altogether
        flattened_packages = [pkg for pkgs in crawled_dict.values() for pkg in pkgs]
        # then we batch that list as if it were a local distro
        batched_packages = self.batch_packages(flattened_packages)

        logger.debug("batched_packages=\n{}".format(pp.pformat(batched_packages)))
        return batched_packages

    @staticmethod
    def _reparent_link(base_path, release, link_name):
        build_link_path = os.path.join(base_path, 'lib/modules', release, link_name)
        build_link_target = os.readlink(build_link_path)
        if build_link_target.startswith('/'):
            build_link_target = '../../..' + build_link_target
            os.unlink(build_link_path)
            os.symlink(build_link_target, build_link_path)

    def unpack_kernels(self, workspace, distro, kernels):
        kernel_dirs = list()

        for release, debs in kernels.items():
            # we can no longer use '-' as the separator, since now also have variant
            # (e.g. cloud-amd64)
            version, vararch = release.rsplit(':', 1)
            # restore the original composite e.g. 5.16.0-1-cloud-amd64
            release = release.replace(':', '-')

            target = workspace.subdir('build', distro, version)

            try:
                for deb in debs:
                    deb_basename = os.path.basename(deb)
                    marker = os.path.join(target, '.' + deb_basename)
                    toolkit.unpack_deb(workspace, deb, target, marker)
                kernel_dirs.append((release, target))
            except:
                traceback.print_exc()

        for release, target in kernel_dirs:
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
        # e.g. linux-headers-|5.10.0-8|-|amd64  |_5.10.46-5_amd64.deb
        #                    | version| |vararch| <ignored>
        #
        # fortunately, we unpack to 5.10.0-8 and look for 5.10.0-8-amd64 inside
        # so we can easily find the requested directory name from the release
        # also, for every minor kernel version (like 5.10) there's a matching
        # kbuild-x.xx package that we need to include in the build directory

        common_packages = {}
        arch_packages = {}
        kbuild_packages = {}


        # Step 1: we loop over all files and we arrange them in 3 buckets:
        # kbuild_packages = { '5.16': 'file' }
        # common_packages = { '5.16.0-1': ['files...'] }
        # arch_packages = { '5.16.0-1': { 'rt-amd64': ['files...'] } }

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
            vararch = m.group('vararch')

            if 'common' in vararch:
                #
                # linux-headers-5.16.0-1-|common|_5.16.7-2_all.deb
                # linux-headers-5.16.0-1-|common-rt|_5.16.7-2_all.deb
                #
                common_packages.setdefault(version, []).append(deb)
            else:
                #
                # linux-headers-5.16.0-1-|rt-amd64|_5.16.7-2_amd64.deb
                # linux-image-5.16.0-1-|amd64|_5.16.7-2_amd64.deb
                # linux-image-5.16.0-1-|cloud-amd64|_5.16.7-2_amd64.deb
                # linux-image-5.16.0-1-|rt-amd64|_5.16.7-2_amd64.deb
                #
                arch_packages.setdefault(version, {}).setdefault(vararch, []).append(deb)


        # Step 2: we compose a dictionary
        #  { '5.16-0-1:rt-amd64' : [ 'linux-headers-5.16.0-1-|rt-amd64|_5.16.7-2_amd64.deb'  (from arch_packages)
        #                             'linux-headers-5.16.0-1-|common|_5.16.7-2_all.deb'      (from common_packages)
        #                             'linux-headers-5.16.0-1-|common-rt|_5.16.7-2_all.deb'   (from common_packages)
        #                             'linux-kbuild-5.16....'                                 (from kbuild_packages)
        #     ]
        #  }
        for version, per_vararch in arch_packages.items():
            for vararch, packages in per_vararch.items():
                packages.extend(common_packages.get(version, []))
                major, minor, _ = version.split('.', 2)
                major_version = '{}.{}'.format(major, minor)
                kbuild_pkg = kbuild_packages.get(major_version)
                if kbuild_pkg:
                    packages.append(kbuild_pkg)
                kernels['{}:{}'.format(version, vararch)] = packages

        return kernels
