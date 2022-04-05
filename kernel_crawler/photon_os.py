from . import rpm
from . import repo


class PhotonOsRepository(rpm.RpmRepository):
    @classmethod
    def kernel_package_query(cls):
        return '''((name = 'linux' OR name LIKE 'linux-%devel%') AND name NOT LIKE '%esx%')'''


class PhotonOsMirror(repo.Distro):
    PHOTON_OS_VERSIONS = [
        ('3.0', '_release'),
        ('3.0', '_updates'),
        ('4.0', ''),
        ('4.0', '_release'),
        ('4.0', '_updates'),
    ]

    def __init__(self, arch='x86_64'):
        if arch=='arm':
            arch='aarch64'
        super(PhotonOsMirror, self).__init__([], arch)

    def list_repos(self):
        return [
            PhotonOsRepository('https://packages.vmware.com/photon/{v}/photon{r}_{v}_{a}/'.format(
                v=version, r=repo_tag, a=self.arch))
            for version, repo_tag in self.PHOTON_OS_VERSIONS]
