import logging
import os
import sys

import click

from probe_builder.kernel_crawler import crawl_kernels, DISTROS
from . import kernel_crawler, disable_ipv6, git, docker
from .builder import choose_builder, builder_image
from .builder.distro import Distro
from .context import Context, Workspace, Probe, DownloadConfig

logger = logging.getLogger(__name__)


def init_logging(debug):
    level = 'DEBUG' if debug else 'INFO'
    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    handler.setLevel(level)
    logger.addHandler(handler)


def get_probe(workspace, sysdig_dir, probe_name, probe_version):
    workspace_dir = workspace.workspace

    try:
        probe_device_name, _ = probe_name.split('-', 1)
    except ValueError:
        probe_device_name = probe_name

    if sysdig_dir is None:
        sysdig_dir = os.path.join(workspace_dir, 'sysdig')
        if probe_device_name == 'sysdigcloud':
            repo = 'https://github.com/draios/agent-libs'
            branch = 'agent/{}'.format(probe_version)
        elif probe_device_name == 'sysdig':
            repo = 'https://github.com/draios/sysdig'
            branch = probe_version
        else:
            raise RuntimeError('Unsupported probe type {}'.format(probe_name))
        git.clone(repo, branch, sysdig_dir)
    else:
        sysdig_dir = os.path.abspath(sysdig_dir)

    if not os.path.exists(sysdig_dir):
        click.echo('Driver source directory {} does not exist'.format(sysdig_dir), err=True)
        sys.exit(1)

    return Probe(sysdig_dir, probe_name, probe_version, probe_device_name)


class CrawlDistro(object):

    def __init__(self, distro, builder_distro, crawler_distro):
        self.distro_obj = Distro(distro, builder_distro)
        self.distro_builder = self.distro_obj.builder()
        self.crawler_distro = crawler_distro

    def get_kernels(self, workspace, _packages, download_config):
        return self.distro_builder.crawl(workspace, self.distro_obj, self.crawler_distro, download_config)


class LocalDistro(object):

    def __init__(self, distro, builder_distro):
        self.distro_obj = Distro(distro, builder_distro)
        self.distro_builder = self.distro_obj.builder()

    def get_kernels(self, _workspace, packages, _download_config):
        return self.distro_builder.batch_packages(packages)


CLI_DISTROS = {
    'AmazonLinux': CrawlDistro('amazonlinux', 'centos', 'AmazonLinux'),
    'AmazonLinux2': CrawlDistro('amazonlinux2', 'centos', 'AmazonLinux2'),
    'CentOS': CrawlDistro('centos', 'centos', 'CentOS'),
    'Debian': CrawlDistro('debian', 'debian', 'Debian'),
    'Fedora': CrawlDistro('fedora', 'centos', 'Fedora'),
    'OracleOL6': None,
    'OracleOL7': None,
    'OracleRHCK': None,
    'Ubuntu': CrawlDistro('ubuntu', 'ubuntu', 'Ubuntu'),
    'CustomCentOS': LocalDistro('custom-centos', 'centos'),
    'CustomDebian': LocalDistro('custom-debian', 'debian'),
    'CustomUbuntu': LocalDistro('custom-ubuntu', 'ubuntu'),
}


@click.group()
@click.option('--debug/--no-debug')
def cli(debug):
    init_logging(debug)


@click.command()
@click.option('-b', '--builder-image-prefix', default='')
@click.option('-d', '--download-concurrency', type=click.INT, default=1)
@click.option('-k', '--kernel-type', type=click.Choice(sorted(CLI_DISTROS.keys())))
@click.option('-p', '--probe-name')
@click.option('-r', '--retries', type=click.INT, default=1)
@click.option('-s', '--source-dir')
@click.option('-t', '--download-timeout', type=click.FLOAT)
@click.option('-v', '--probe-version')
@click.argument('package', nargs=-1)
def build(builder_image_prefix,
          download_concurrency, kernel_type, probe_name, retries,
          source_dir, download_timeout, probe_version, package):
    workspace_dir = os.getcwd()
    builder_source = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    workspace = Workspace(docker.get_mount_mapping(), workspace_dir, builder_source, builder_image_prefix)
    probe = get_probe(workspace, source_dir, probe_name, probe_version)
    distro_obj = CLI_DISTROS[kernel_type]

    distro_builder = distro_obj.distro_builder
    distro = distro_obj.distro_obj
    download_config = DownloadConfig(download_concurrency, download_timeout, retries, None)

    kernels = distro_obj.get_kernels(workspace, package, download_config)
    kernel_dirs = distro_builder.unpack_kernels(workspace, distro.distro, kernels)
    for release, target in kernel_dirs.items():
        distro_builder.build_kernel(workspace, probe, distro.builder_distro, release, target)


@click.command()
@click.argument('distro', type=click.Choice(sorted(DISTROS.keys())))
@click.argument('version', required=False, default='')
def crawl(distro, version=''):
    kernels = crawl_kernels(distro, version)
    for release, packages in kernels.items():
        print('=== {} ==='.format(release))
        for pkg in packages:
            print(' {}'.format(pkg))


cli.add_command(build, 'build')
cli.add_command(crawl, 'crawl')

if __name__ == '__main__':
    cli()
