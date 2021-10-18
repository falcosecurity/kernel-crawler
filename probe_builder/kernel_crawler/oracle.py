from . import repo
from . import rpm


class OracleRepository(rpm.RpmRepository):
    @classmethod
    def kernel_package_query(cls):
        return '''(name IN ('kernel', 'kernel-devel', 'kernel-uek', 'kernel-uek-devel') AND arch = 'x86_64')'''


class Oracle6Mirror(repo.Distro):
    OL6_REPOS = [
        'http://yum.oracle.com/repo/OracleLinux/OL6/latest/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL6/MODRHCK/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL6/UEKR4/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL6/UEKR3/latest/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL6/UEK/latest/x86_64/',

    ]

    def __init__(self):
        super(Oracle6Mirror, self).__init__([])

    def list_repos(self):
        return [OracleRepository(url) for url in self.OL6_REPOS]


class Oracle7Mirror(repo.Distro):
    OL7_REPOS = [
        'http://yum.oracle.com/repo/OracleLinux/OL7/latest/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL7/MODRHCK/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR6/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR5/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR4/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR3/x86_64/',
    ]

    def __init__(self):
        super(Oracle7Mirror, self).__init__([])

    def list_repos(self):
        return [OracleRepository(url) for url in self.OL7_REPOS]


class Oracle8Mirror(repo.Distro):
    OL8_REPOS = [
        'http://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL8/UEKR6/x86_64/',
    ]

    def __init__(self):
        super(Oracle8Mirror, self).__init__([])

    def list_repos(self):
        return [OracleRepository(url) for url in self.OL8_REPOS]
