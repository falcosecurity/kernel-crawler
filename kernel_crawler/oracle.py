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

    def __init__(self, arch='x86_64'):
        if arch=='arm':
            arch='aarch64'
        super(Oracle6Mirror, self).__init__([], arch)

    def list_repos(self):
        return [OracleRepository(url) for url in self.repos()]


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

    def __init__(self, arch='x86_64'):
        if arch=='arm':
            arch='aarch64'
        super(Oracle7Mirror, self).__init__([], arch)

    def list_repos(self):
        return [OracleRepository(url) for url in self.repos()]


class Oracle8Mirror(repo.Distro):
    def repos(self):
        return [
            'http://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL8/UEKR6/' + self.arch + '/',
        ]

    def __init__(self, arch='x86_64'):
        if arch=='arm':
            arch='aarch64'
        super(Oracle8Mirror, self).__init__([], arch)

    def list_repos(self):
        return [OracleRepository(url) for url in self.repos()]