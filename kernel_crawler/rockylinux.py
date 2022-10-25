from . import repo
from . import rpm

def v8_only(ver):
    return ver.startswith('8')

def v9_only(ver):
    return ver.startswith('9')

class RockyLinuxMirror(repo.Distro):
    def __init__(self, arch):
        mirrors = [
            # Rocky Linux 8
            rpm.RpmMirror('http://dl.rockylinux.org/pub/rocky/', 'BaseOS/' + arch + '/os/', v8_only),
            rpm.RpmMirror('http://dl.rockylinux.org/pub/rocky/', 'AppStream/' + arch + '/os/', v8_only),
            rpm.RpmMirror('http://dl.rockylinux.org/vault/rocky/', 'BaseOS/' + arch + '/os/', v8_only),
            # Rocky Linux 9
            rpm.RpmMirror('http://dl.rockylinux.org/pub/rocky/', 'BaseOS/' + arch + '/os/', v9_only),
            rpm.RpmMirror('http://dl.rockylinux.org/pub/rocky/', 'AppStream/' + arch + '/os/', v9_only),
            # Valut repo not yet available for Rocky Linux 9
            #rpm.RpmMirror('http://dl.rockylinux.org/vault/rocky/', v9_only, 'BaseOS/' + arch + '/os/'),
        ]
        super(RockyLinuxMirror, self).__init__(mirrors, arch)

    def to_driverkit_config(self, release, deps):
        for dep in deps:
            if dep.find("devel") != -1:
                return repo.DriverKitConfig(release, "rocky", dep)
