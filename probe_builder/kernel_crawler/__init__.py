from .amazonlinux import AmazonLinux1Mirror, AmazonLinux2Mirror
from .centos import CentosMirror
from .fedora import FedoraMirror
from .oracle import Oracle6Mirror, Oracle7Mirror, Oracle8Mirror
from .photon_os import PhotonOsMirror

from .debian import DebianMirror
from .ubuntu import UbuntuMirror

from .flatcar import FlatcarMirror

DISTROS = {
    'AmazonLinux': {AmazonLinux1Mirror},
    'AmazonLinux2': {AmazonLinux2Mirror},
    'CentOS': {CentosMirror},
    'Fedora': {FedoraMirror},
    'Oracle6': {Oracle6Mirror},
    'Oracle7': {Oracle7Mirror},
    'Oracle8': {Oracle8Mirror},
    'PhotonOS': {PhotonOsMirror},

    'Debian': {DebianMirror},
    'Ubuntu': {UbuntuMirror},

    'Flatcar': {FlatcarMirror},

    '*': {AmazonLinux1Mirror, AmazonLinux2Mirror, CentosMirror, FedoraMirror, Oracle6Mirror, Oracle7Mirror,
          Oracle8Mirror, PhotonOsMirror, DebianMirror, UbuntuMirror, FlatcarMirror},
}


def crawl_kernels(distro, version='', arch=''):
    dist = DISTROS[distro]
    ret = {}
    for d in dist:
        if arch:
            ret.update(d(arch).get_package_tree(version))
        else:
            ret.update(d().get_package_tree(version))
    return ret
