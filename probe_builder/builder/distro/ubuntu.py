import logging
import os
import re
import pprint

import click

from probe_builder.builder import toolkit
from .base_builder import DistroBuilder

logger = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(depth=4)

class UbuntuBuilder(DistroBuilder):
    KERNEL_VERSION_RE = re.compile(r'(?P<version>[0-9]\.[0-9]+\.[0-9]+-[0-9]+)\.(?P<update>[0-9][^_]*)')
    KERNEL_RELEASE_RE = re.compile(r'(?P<release>[0-9]\.[0-9]+\.[0-9]+-[0-9]+-[a-z0-9-]+)')

    def crawl(self, workspace, distro, crawler_distro, download_config=None, filter=''):
        crawled_dict = super().crawl(workspace=workspace, distro=distro, crawler_distro=crawler_distro, download_config=download_config, filter=filter)
        kernels = []
        # batch packages according to package version, e.g. '5.15.0-1001/1' as returned by the crawler
        # (which is the package version of the main 'linux-headers-5.15.0-1001-gke_5.15.0-1001.1_amd64.deb')
        # each of those versions may yield one or more releases e.g. '5.15.0-1001-gke'
        for version, flattened_packages in crawled_dict.items():
            # since the returned value is a list of tuple, we just extend them
            kernels.extend(self.batch_packages(flattened_packages, version))
        return kernels

    def unpack_kernels(self, workspace, distro, kernels):
        kernel_dirs = list()

        # notice how here kernels is a list of tuples
        # ( '5.4.0-1063-aws', [".._5.4.0-1063.66_amd64.deb"] )
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
                    if version[0] != new_version[0] and not new_version[1].startswith(version[1]):
                        raise ValueError("Unexpected version {}/{} from package {} (expected {}/{})".format(
                            new_version[0], new_version[1], deb,
                            version[0], version[1]
                        ))
            # extracted files will end up in a directory derived from the version
            # e.g. 5.4.0-1063/66
            target = workspace.subdir('build', distro, version[0], version[1])
            # which we will address by release
            # ( '5.4.0-1063-aws', '/path/to/5.4.0-1063/66' )
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

    def batch_packages(self, kernel_files, expected_version=None):
        kernels = []

        # ubuntu kernels have two separate versions
        # e.g. the package linux-headers-5.4.0-86-generic_5.4.0-86.97_amd64.deb
        # has a "version" (used in the target dir) of 5.4.0-86/97
        #    which is effectively the deb package version
        # and a "release" (describing the paths inside the archive) of 5.4.0-86-generic
        #    which is effectively part of the deb package name
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


        # Step 1: allocate all packages between two buckets:
        # version_files = {'5.4.0-1063/66': ['...linux-aws-headers-5.4.0-1063_5.4.0-1063.66_all.deb',
        #           '...linux-azure-headers-5.4.0-1063_5.4.0-1063.66_all.deb',
        #           '...linux-gke-headers-5.4.0-1063_5.4.0-1063.66_amd64.deb'],
        # releases =
        # {('5.4.0-1063-aws', '5.4.0-1063/66'): ['..linux-modules-5.4.0-1063-aws_5.4.0-1063.66_amd64.deb',
        #                                        '...linux-headers-5.4.0-1063-aws_5.4.0-1063.66_amd64.deb'],
        # ('5.4.0-1063-azure', '5.4.0-1063/66'): ['...linux-modules-5.4.0-1063-azure_5.4.0-1063.66_amd64.deb',
        #                                         '...linux-headers-5.4.0-1063-azure_5.4.0-1063.66_amd64.deb'],
        # ('5.4.0-1063-gke', '5.4.0-1063/66'): ['...linux-headers-5.4.0-1063-gke_5.4.0-1063.66_amd64.deb',
        #                                       '...linux-modules-5.4.0-1063-gke_5.4.0-1063.66_amd64.deb'],
        # and also build a map
        # version_to_releases = {'5.4.0-1063/66': {'5.4.0-1063-gke', '5.4.0-1063-azure', '5.4.0-1063-aws'},
        #
        # this essentially means that for each unique "version" we can find across all .deb packages


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

            if expected_version:
                if version.startswith(expected_version):
                    version = expected_version
                else:
                    raise ValueError("Unexpected version {} from package {} (expected to start with {})".format(
                                version, deb, expected_version))


            # linux-headers-|5.4.0-1063-azure-cvm|_5.4.0-1063.66+cvm3_amd64.deb
            m = self.KERNEL_RELEASE_RE.search(deb_basename)
            if m:
                release = m.group('release')
                version_to_releases.setdefault(version, set()).add(release)
                logger.debug("release-file: release={}, version={}, deb={}".format(release, version, deb))
                releases.setdefault((release, version), []).append(deb)
            else:
                logger.debug("non-release-file: version={}, deb={}".format(version, deb))
                version_files.setdefault(version, []).append(deb)


        logger.debug("version_files=\n{}".format(pp.pformat(version_files)))
        logger.debug("releases=\n{}".format(pp.pformat(releases)))
        logger.debug("version_to_releases=\n{}".format(pp.pformat(version_to_releases)))

        # Step 2: provide the final list (note: a list, not a dict!) where the first element
        #           is the 'release'
        # [  ('5.4.0-1063-aws',
        #    ['/workspace/ubuntu/linux-modules-5.4.0-1063-aws_5.4.0-1063.66_amd64.deb',
        #    '/workspace/ubuntu/linux-headers-5.4.0-1063-aws_5.4.0-1063.66_amd64.deb',
        #    '/workspace/ubuntu/linux-azure-headers-5.4.0-1063_5.4.0-1063.66_all.deb',
        #    '/workspace/ubuntu/linux-aws-headers-5.4.0-1063_5.4.0-1063.66_all.deb',
        #    '/workspace/ubuntu/linux-gke-headers-5.4.0-1063_5.4.0-1063.66_amd64.deb']),
        #]

        for version, release_ids in version_to_releases.items():
            for release_id in release_ids:
                release_files = releases[(release_id, version)]
                # add all the shared files that end up in the same directory
                release_files.extend(version_files.get(version, []))
                kernels.append((release_id, release_files))

        logger.debug("kernels=\n{}".format(pp.pformat(kernels)))
        return kernels
