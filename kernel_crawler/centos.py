from . import repo
from . import rpm

def v7_only(ver):
    return ver.startswith('7')

def v8_only(ver):
    return ver.startswith('8')

def v9_only(ver):
    return ver.startswith('9')

def v6_or_v7(ver):
    return ver.startswith('6') or ver.startswith('7')

class CentosMirror(repo.Distro):
    def __init__(self, arch):
        mirrors = [
            rpm.RpmMirror('http://mirror.centos.org/centos/', 'os/' + arch + '/',  v7_only),
            rpm.RpmMirror('http://mirror.centos.org/centos/', 'updates/' + arch + '/', v7_only),
            # CentOS 8 reached end-of-life at the end of 2021, so no point looking for it
            # rpm.RpmMirror('http://mirror.centos.org/centos/', 'BaseOS/' + arch + '/os/', v8_only),
            rpm.RpmMirror('http://vault.centos.org/centos/', 'os/' + arch + '/', v6_or_v7),
            rpm.RpmMirror('http://vault.centos.org/centos/', 'updates/' + arch + '/', v6_or_v7),
            rpm.RpmMirror('http://vault.centos.org/centos/', 'BaseOS/' + arch + '/os/', v8_only),
            rpm.RpmMirror('http://archive.kernel.org/centos/', 'os/' + arch + '/', v6_or_v7),
            rpm.RpmMirror('http://archive.kernel.org/centos/', 'updates/' + arch + '/', v6_or_v7),
            rpm.RpmMirror('http://archive.kernel.org/centos/', 'BaseOS/' + arch + '/os/', v8_only),
            # It seems like centos stream uses /AppStream for kernel-devel, instead of BaseOS
            rpm.RpmMirror('http://mirror.stream.centos.org/', 'BaseOS/' + arch + '/os/', v9_only),
            rpm.RpmMirror('http://mirror.stream.centos.org/', 'AppStream/' + arch + '/os/', v9_only)
        ]
        super(CentosMirror, self).__init__(mirrors, arch)

    def to_driverkit_config(self, release, deps):
        for dep in deps:
            if dep.find("devel") != -1:
                return repo.DriverKitConfig(release, "centos", dep)