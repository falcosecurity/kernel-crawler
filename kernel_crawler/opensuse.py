from . import repo
from . import rpm

from lxml import etree, html
from bs4 import BeautifulSoup
from kernel_crawler.utils.download import get_url

import requests
import sys


class OpenSUSEMirror(repo.Distro):

    def __init__(self, arch):
        mirrors = [
            # leap
            rpm.SUSERpmMirror('https://mirrors.edge.kernel.org/opensuse/distribution/leap/', 'repo/oss/', arch),
            rpm.SUSERpmMirror('https://mirrors.edge.kernel.org/opensuse/distribution/leap/', 'repo/oss/suse/', arch),
            # the rest
            rpm.SUSERpmMirror('https://mirrors.edge.kernel.org/opensuse/distribution/', 'repo/oss/', arch),
            rpm.SUSERpmMirror('https://mirrors.edge.kernel.org/opensuse/distribution/', 'repo/oss/suse/', arch),
        ]

        super(OpenSUSEMirror, self).__init__(mirrors, arch)

    def to_driverkit_config(self, release, deps):
        for dep in deps:
            if dep.find("devel") != -1:
                return repo.DriverKitConfig(release, "opensuse", dep)
