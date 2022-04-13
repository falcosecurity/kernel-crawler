from . import deb
from . import repo
from .debian import fixup_deb_arch

class UbuntuMirror(repo.Distro):
    def __init__(self, arch):
        arch = fixup_deb_arch(arch)
        mirrors = [
            deb.DebMirror('http://mirrors.edge.kernel.org/ubuntu/', arch),
            deb.DebMirror('http://security.ubuntu.com/ubuntu/', arch),
            deb.DebMirror('http://ports.ubuntu.com/ubuntu-ports/', arch),
        ]
        super(UbuntuMirror, self).__init__(mirrors, arch)

    def to_driverkit_config(self, release, deps):
        krel, kver = release.split("/")
        target = "ubuntu-generic"
        for dep in deps:
            # We only support ubuntu-aws specific builder in driverkit
            d = dep.find("aws")
            if d != -1:
                target = "ubuntu-aws"
                krel += "-aws"
            else:
                krel += "-generic"
            break
        return repo.DriverKitConfig(krel, target, kver)