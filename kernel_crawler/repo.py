from __future__ import print_function
from . import container

import click
import sys

class Repository(object):
    def get_package_tree(self, version=''):
        raise NotImplementedError

    def __str__(self):
        raise NotImplementedError

class DriverKitConfig(object):
    def __init__(self, kernelrelease, target, headers, kernelversion=1):
        self.kernelversion = kernelversion
        self.kernelrelease = kernelrelease
        self.target = target
        if isinstance(headers, list):
            self.headers = headers
        else:
            # Fake single-list
            self.headers = [headers]

def to_s(s):
    if s is None:
        return ''
    return str(s)


class Mirror(object):
    def __init__(self, arch):
        self.arch = arch

    def list_repos(self,):
        raise NotImplementedError

    def get_package_tree(self, version=''):
        packages = {}
        repos = self.list_repos()
        with click.progressbar(repos, label='Listing packages', file=sys.stderr, item_show_func=to_s) as repos:
            for repo in repos:
                for release, dependencies in repo.get_package_tree(version).items():
                    packages.setdefault(release, set()).update(dependencies)
        return packages


class Distro(Mirror):
    def __init__(self, mirrors, arch):
        self.mirrors = mirrors
        super().__init__(arch)

    def list_repos(self):
        repos = []
        with click.progressbar(
                self.mirrors, label='Checking repositories', file=sys.stderr, item_show_func=to_s) as mirrors:
            for mirror in mirrors:
                repos.extend(mirror.list_repos())
        return repos


class ContainerDistro(container.Container):
    def __init__(self, container_name):
        super(ContainerDistro, self).__init__(container_name)

    def get_kernel_versions(self):
        raise NotImplementedError