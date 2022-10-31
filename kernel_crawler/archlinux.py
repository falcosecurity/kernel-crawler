from bs4 import BeautifulSoup
import re

from kernel_crawler.utils.download import get_url
from . import repo

class ArchLinuxRepository(repo.Repository):

    _linux_headers_pattern = 'linux.*headers-'
    _package_suffix_pattern = '.pkg.tar.*'

    def __init__(self, base_url):
        self.base_url = base_url

    def __str__(self):
        return self.base_url

    def parse_kernel_release(self, kernel_package):

        trimmed = re.sub(self._linux_headers_pattern, '', kernel_package)
        version = re.sub(self._package_suffix_pattern, '', trimmed)

        return version

    def get_package_tree(self, filter=''):
        packages = {}

        soup = BeautifulSoup(get_url(self.base_url), features='lxml')
        for a in soup.find_all('a', href=True):
            package = a['href']
            # skip .sig and .. links
            if not package.endswith('.sig') and package != '../':
                parsed_kernel_release = self.parse_kernel_release(package)

                packages.setdefault(parsed_kernel_release, set()).add(self.base_url + package)

        return packages


class ArchLinuxMirror(repo.Distro):

    _base_urls = [
        'https://archive.archlinux.org/packages/l/linux-headers/',           # stable
        'https://archive.archlinux.org/packages/l/linux-hardened-headers/',  # hardened
        'https://archive.archlinux.org/packages/l/linux-lts-headers/',       # lts
        'https://archive.archlinux.org/packages/l/linux-zen-headers/',       # zen
    ]

    def __init__(self, arch):
        super(ArchLinuxMirror, self).__init__(self._base_urls, arch)


    def list_repos(self):
        mirrors = []

        for mirror in self._base_urls:
            mirrors.append(ArchLinuxRepository(mirror))

        return mirrors


    def to_driverkit_config(self, release, deps):
        for dep in deps:
            return repo.DriverKitConfig(release, "arch", dep)
