from . import repo
from . import deb
import click
import sys


def repo_filter(dist):
    return 'stable' not in dist and 'testing' not in dist and not dist.startswith('Debian')


class DebianLikeMirror(repo.Distro):

    def get_package_tree(self, version=''):
        all_packages = {}
        all_kernel_packages = []
        packages = {}
        repos = self.list_repos()
        with click.progressbar(repos, label='Listing packages', file=sys.stderr, item_show_func=repo.to_s) as repos:
            for repository in repos:
                repo_packages = repository.get_raw_package_db()
                all_packages.update(repo_packages)
                kernel_packages = repository.get_package_list(repo_packages, version)
                all_kernel_packages.extend(kernel_packages)

        for release, dependencies in deb.DebRepository.build_package_tree(all_packages, all_kernel_packages).items():
            packages.setdefault(release, set()).update(dependencies)
        return packages


class DebianMirror(DebianLikeMirror):
    def __init__(self):
        mirrors = [
            deb.DebMirror('https://mirrors.edge.kernel.org/debian/', repo_filter),
            deb.DebMirror('http://security.debian.org/', repo_filter),
        ]
        super(DebianMirror, self).__init__(mirrors)
