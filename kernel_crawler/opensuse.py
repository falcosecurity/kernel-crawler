from . import repo
from . import rpm

from lxml import etree, html
from bs4 import BeautifulSoup
from kernel_crawler.utils.download import get_url

import requests
import sys

def opensuse_filter(dist):
    return not dist.startswith('linux-next') \
    and (
        dist.startswith('openSUSE')   or
        dist.startswith('./openSUSE') or
        dist.startswith('HEAD')       or
        dist.startswith('stable')
    )

def tumbleweed_filter(dist):
    return dist.startswith('tumbleweed')


class OpenSUSEMirror(repo.Distro):

    def __init__(self, arch):
        mirrors = [
            # leap
            rpm.SUSERpmMirror('https://mirrors.edge.kernel.org/opensuse/distribution/leap/', 'repo/oss/', arch),
            rpm.SUSERpmMirror('https://mirrors.edge.kernel.org/opensuse/distribution/leap/', 'repo/oss/suse/', arch),
            # the rest
            rpm.SUSERpmMirror('https://mirrors.edge.kernel.org/opensuse/distribution/', 'repo/oss/', arch),
            rpm.SUSERpmMirror('https://mirrors.edge.kernel.org/opensuse/distribution/', 'repo/oss/suse/', arch),
            # opensuse site: tumbleweed
            rpm.SUSERpmMirror('http://download.opensuse.org/', 'repo/oss/', arch, tumbleweed_filter),
            # opensuse site: leaps
            rpm.SUSERpmMirror('http://download.opensuse.org/distribution/leap/', 'repo/oss/', arch),
        ]

        # other arch's are stored differently on SUSE's site
        # in general, the /repositories/Kernel:/ are stored differently and require a filter
        if arch == 'x86_64':
            mirrors.append(rpm.SUSERpmMirror('https://download.opensuse.org/repositories/Kernel:/', 'Submit/standard/', arch, opensuse_filter))
            mirrors.append(rpm.SUSERpmMirror('https://download.opensuse.org/repositories/Kernel:/', 'standard/', arch, opensuse_filter))
        else:
            mirrors.append(rpm.SUSERpmMirror('https://download.opensuse.org/repositories/Kernel:/', 'Submit/ports/', arch, opensuse_filter))
            mirrors.append(rpm.SUSERpmMirror('https://download.opensuse.org/repositories/Kernel:/', 'ports/', arch, opensuse_filter))

        super(OpenSUSEMirror, self).__init__(mirrors, arch)

    def to_driverkit_config(self, release, deps):
        for dep in deps:
            if dep.find("devel") != -1:
                return repo.DriverKitConfig(release, "opensuse", dep)
