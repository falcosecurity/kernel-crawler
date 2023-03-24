from . import repo
from . import rpm


class OracleRepository(rpm.RpmRepository):
    @classmethod
    def kernel_package_query(cls):
        return '''(name IN ('kernel', 'kernel-devel', 'kernel-uek', 'kernel-uek-devel') AND arch = 'x86_64')'''


class OracleMirror(repo.Distro):
    def repos(self):
        return [
            # Oracle6
            'http://yum.oracle.com/repo/OracleLinux/OL6/latest/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL6/MODRHCK/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL6/UEKR4/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL6/UEKR3/latest/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL6/UEK/latest/' + self.arch + '/',
            # Oracle7
            'http://yum.oracle.com/repo/OracleLinux/OL7/latest/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL7/MODRHCK/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR6/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR5/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR4/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR3/' + self.arch + '/',
            # Oracle8
            'http://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL8/UEKR6/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL8/appstream/' + self.arch + '/',
            # Oracle9
            'http://yum.oracle.com/repo/OracleLinux/OL9/baseos/latest/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL9/UEKR7/' + self.arch + '/',
            'http://yum.oracle.com/repo/OracleLinux/OL9/appstream/' + self.arch + '/',
        ]

    def __init__(self, arch):
        super(OracleMirror, self).__init__([], arch)

    def list_repos(self):
        return [OracleRepository(url) for url in self.repos()]

    def to_driverkit_config(self, release, deps):
        for dep in deps:
            if dep.find("devel") != -1:
                return repo.DriverKitConfig(release, "ol", dep)
