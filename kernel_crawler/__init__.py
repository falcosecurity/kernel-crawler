from .amazonlinux import AmazonLinux1Mirror, AmazonLinux2Mirror
from .centos import CentosMirror
from .fedora import FedoraMirror
from .oracle import Oracle6Mirror, Oracle7Mirror, Oracle8Mirror
from .photon_os import PhotonOsMirror

from .debian import DebianMirror
from .ubuntu import UbuntuMirror

from .flatcar import FlatcarMirror

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

    'Flatcar': FlatcarMirror,
}


def to_driverkit_config(d, res):
    dk_configs = []
    for ver, deps in res.items():
        dk_configs.append(d.to_driverkit_config(ver, deps))
    return dk_configs

def crawl_kernels(distro, version, arch, to_driverkit):
    ret = {}

    for distname, dist in DISTROS.items():
        if distname == distro or distro == "*":
            d = dist(arch)
            res = d.get_package_tree(version)
            if to_driverkit:
                ret[distname] = to_driverkit_config(d, res)
            else:
                ret[distname] = res

    return ret
