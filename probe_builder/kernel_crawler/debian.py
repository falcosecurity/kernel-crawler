from . import repo
from . import deb
import click
import sys


def repo_filter(dist):
    return 'stable' not in dist and 'testing' not in dist and not dist.startswith('Debian')


class DebianMirror(repo.Distro):
    def __init__(self):
        mirrors = [
            deb.DebMirror('http://mirrors.edge.kernel.org/debian/', repo_filter),
            deb.DebMirror('http://security.debian.org/', repo_filter),
        ]
        super(DebianMirror, self).__init__(mirrors)

    # For Debian mirrors, we need to override this method so that dependencies
    # can be resolved (i.e. build_package_tree) across multiple repositories.
    # This is namely required for the linux-kbuild package, which is typically
    # hosted on a different repository compared to the kernel packages
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
