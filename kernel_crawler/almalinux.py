from . import repo
from . import rpm

def v8_only(ver):
    return ver.startswith('8')

def v9_only(ver):
    return ver.startswith('9')

class AlmaLinuxMirror(repo.Distro):
    def __init__(self, arch):
        mirrors = [
            # AlmaLinux 8
            rpm.RpmMirror('http://repo.almalinux.org/almalinux/', 'BaseOS/' + arch + '/os/', v8_only),
            rpm.RpmMirror('http://repo.almalinux.org/almalinux/', 'AppStream/' + arch + '/os/', v8_only),
            # AlmaLinux 9
            rpm.RpmMirror('http://repo.almalinux.org/almalinux/', 'BaseOS/' + arch + '/os/', v9_only),
            rpm.RpmMirror('http://repo.almalinux.org/almalinux/', 'AppStream/' + arch + '/os/', v9_only),
        ]
        super(AlmaLinuxMirror, self).__init__(mirrors, arch)

    def to_driverkit_config(self, release, deps):
        for dep in deps:
            if dep.find("devel") != -1:
                return repo.DriverKitConfig(release, "almalinux", dep)