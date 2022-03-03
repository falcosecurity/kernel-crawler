import errno
import glob
import logging
import os
import subprocess

import click

from .base_builder import DistroBuilder, to_s
from .. import toolkit, builder_image
from ... import crawl_kernels, docker
from ...kernel_crawler.download import download_file

logger = logging.getLogger(__name__)


class FlatcarBuilder(DistroBuilder):
    def unpack_kernels(self, workspace, distro, kernels):
        kernel_dirs = list()

        for release, dev_containers in kernels.items():
            target = workspace.subdir('build', distro, release)
            kernel_dirs.append((release, target))

            for dev_container in dev_containers:
                dev_container_basename = os.path.basename(dev_container)
                marker = os.path.join(target, '.' + dev_container_basename)
                toolkit.unpack_coreos(workspace, dev_container, target, marker)

        return kernel_dirs

    def hash_config(self, release, target):
        return self.md5sum(os.path.join(target, 'config'.format(release)))

    def get_kernel_dir(self, workspace, release, target):
        versions = glob.glob(os.path.join(target, 'modules/*/build'))
        if len(versions) != 1:
            raise RuntimeError('Expected one kernel version in {}, got: {!r}'.format(target, versions))
        return versions[0]

    def batch_packages(self, kernel_files):
        releases = {}
        for path in kernel_files:
            release, orig_filename = os.path.basename(path).split('-', 1)
            releases.setdefault(release, []).append(path)
        return releases

    @classmethod
    def build_kernel_impl(cls, config_hash, container_name, image_name, kernel_dir, probe, release, workspace, bpf,
                          skip_reason):
        if bpf:
            label = 'eBPF'
            args = ['bpf']
        else:
            label = 'kmod'
            args = []

        coreos_kernel_release = os.path.basename(os.path.dirname(kernel_dir))

        if skip_reason:
            logger.info('Skipping build of {} probe {}-{} ({}): {}'.format(label, coreos_kernel_release, config_hash,
                                                                           release, skip_reason))

        docker.rm(container_name)
        try:
            builder_image.run(workspace, probe, kernel_dir, coreos_kernel_release, config_hash, container_name, image_name, args)
        except subprocess.CalledProcessError:
            logger.error("Build failed for {} probe {}-{} ({})".format(label, coreos_kernel_release, config_hash, release))
        else:
            logger.info("Build for {} probe {}-{} ({}) successful".format(label, coreos_kernel_release, config_hash, release))

    def crawl(self, workspace, distro, crawler_distro, download_config=None):
        kernels = crawl_kernels(crawler_distro)
        try:
            os.makedirs(workspace.subdir(distro.distro))
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

        all_urls = []
        kernel_files = {}
        for release, urls in kernels.items():
            all_urls.extend(urls)
            kernel_files[release] = [
                workspace.subdir(distro.distro, '{}-{}'.format(release, os.path.basename(url))) for url in urls]

        with click.progressbar(all_urls, label='Downloading development containers', item_show_func=to_s) as all_urls:
            for url in all_urls:
                _, release, filename = url.rsplit('/', 2)
                output_file = workspace.subdir(distro.distro, '{}-{}'.format(release, filename))
                download_file(url, output_file, download_config)

        return kernel_files
