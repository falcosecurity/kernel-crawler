from .amazonlinux import AmazonLinux1Mirror, AmazonLinux2Mirror
from .centos import CentosMirror
from .fedora import FedoraMirror
from .oracle import Oracle6Mirror, Oracle7Mirror, Oracle8Mirror
from .photon_os import PhotonOsMirror

from .debian import DebianMirror
from .ubuntu import UbuntuMirror

DISTROS = {
    'AmazonLinux': AmazonLinux1Mirror,
    'AmazonLinux2': AmazonLinux2Mirror,
    'CentOS': CentosMirror,
    'Fedora': FedoraMirror,
    'Oracle6': Oracle6Mirror,
    'Oracle7': Oracle7Mirror,
    'Oracle8': Oracle8Mirror,
    'PhotonOS': PhotonOsMirror,

    'Debian': DebianMirror,
    'Ubuntu': UbuntuMirror,
}


def crawl_kernels(distro, version=''):
    dist = DISTROS[distro]

    return dist().get_package_tree(version)
