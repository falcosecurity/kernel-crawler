from .minikube import MinikubeMirror
from .amazonlinux import AmazonLinux1Mirror, AmazonLinux2Mirror, AmazonLinux2022Mirror
from .centos import CentosMirror
from .fedora import FedoraMirror
from .oracle import Oracle6Mirror, Oracle7Mirror, Oracle8Mirror
from .photon_os import PhotonOsMirror

from .debian import DebianMirror
from .ubuntu import UbuntuMirror

from .flatcar import FlatcarMirror

from .redhat import RedhatContainer

DISTROS = {
    'AmazonLinux': AmazonLinux1Mirror,
    'AmazonLinux2': AmazonLinux2Mirror,
    'AmazonLinux2022': AmazonLinux2022Mirror,
    'CentOS': CentosMirror,
    'Fedora': FedoraMirror,
    'Oracle6': Oracle6Mirror,
    'Oracle7': Oracle7Mirror,
    'Oracle8': Oracle8Mirror,
    'PhotonOS': PhotonOsMirror,

    'Debian': DebianMirror,
    'Ubuntu': UbuntuMirror,

    'Flatcar': FlatcarMirror,
    
    'Minikube': MinikubeMirror,

    'Redhat': RedhatContainer
}

def to_driverkit_config(d, res):
    dk_configs = []
    # Note, this is not good performance-wise because we are post-processing the list
    # while we could do the same at generation time.
    # But this is much simpler and involved touching less code.
    # Moreover, we do not really care about performance here.
    for ver, deps in res.items():
        dk_conf = d.to_driverkit_config(ver, deps)
        if dk_conf is not None:
            try:
                # Ubuntu returns multiple for each
                dk_configs.extend(dk_conf)
            except TypeError:
                # Others return just a single dk config
                dk_configs.append(dk_conf)

    return dk_configs

def crawl_kernels(distro, version, arch, images, to_driverkit):
    ret = {}

    for distname, dist in DISTROS.items():
        if distname == distro or distro == "*":
            # If the distro requires an image (Redhat only so far), we need to amalgamate
            # the kernel versions from the supplied images before choosing the output.
            if issubclass(dist, repo.ContainerDistro):
                if images:
                    kv = {}
                    for image in images:
                        d = dist(image)
                        if len(kv) == 0:
                            kv = d.get_kernel_versions()
                        else:
                            kv.update(d.get_kernel_versions())
                    # We should now have a list of all kernel versions for the supplied images
                    res = kv
                else:
                    d = None
            else:
                d = dist(arch)
                res = d.get_package_tree(version)

            if d and res:
                if to_driverkit:
                    ret[distname] = to_driverkit_config(d, res)
                else:
                    ret[distname] = res
    return ret
