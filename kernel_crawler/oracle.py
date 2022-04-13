from . import repo
from . import rpm


class OracleRepository(rpm.RpmRepository):
    @classmethod
    def kernel_package_query(cls):
        return '''(name IN ('kernel', 'kernel-devel', 'kernel-uek', 'kernel-uek-devel') AND arch = 'x86_64')'''


class Oracle6Mirror(repo.Distro):
    def repos(self):
        return [
            'http://yum.oracle.com/repo/OracleLinux/OL6/latest/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL6/MODRHCK/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL6/UEKR4/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL6/UEKR3/latest/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL6/UEK/latest/' + self.arch + '/',
        ]

    def __init__(self, arch):
        super(Oracle6Mirror, self).__init__([], arch)

    def list_repos(self):
        return [OracleRepository(url) for url in self.repos()]

    def to_driverkit_config(self, release, deps):
        return repo.DriverKitConfig(release, "oracle6")


class Oracle7Mirror(repo.Distro):
    def repos(self):
        return [
            'http://yum.oracle.com/repo/OracleLinux/OL7/latest/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL7/MODRHCK/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR6/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR5/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR4/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR3/' + self.arch + '/',
        ]

    def __init__(self, arch):
        super(Oracle7Mirror, self).__init__([], arch)

    def list_repos(self):
        return [OracleRepository(url) for url in self.repos()]

    def to_driverkit_config(self, release, deps):
        return repo.DriverKitConfig(release, "oracle7")


class Oracle8Mirror(repo.Distro):
    def repos(self):
        return [
            'http://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL8/UEKR6/' + self.arch + '/',
        ]

    def __init__(self, arch):
        super(Oracle8Mirror, self).__init__([], arch)

    def list_repos(self):
        return [OracleRepository(url) for url in self.repos()]

    def to_driverkit_config(self, release, deps):
        return repo.DriverKitConfig(release, "oracle8")