from . import repo
from . import rpm

def v2_only(ver):
    return ver.startswith('2')

def v3_only(ver):
    return ver.startswith('3')

class AliyunLinuxMirror(repo.Distro):
    def __init__(self, arch):
        mirrors = [
            # AliyunLinux 2
            # Mirror list on cloud-init config example:
            # https://www.alibabacloud.com/help/en/elastic-compute-service/latest/use-alibaba-cloud-linux-2-images-in-an-on-premises-environment
            rpm.RpmMirror('http://mirrors.aliyun.com/alinux/', 'os/' + arch + '/', v2_only),
            rpm.RpmMirror('http://mirrors.aliyun.com/alinux/', 'updates/' + arch + '/', v2_only),
            rpm.RpmMirror('http://mirrors.aliyun.com/alinux/', 'plus/' + arch + '/', v2_only),

            # AliyunLinux 3
            # Mirror list on cloud-init config example:
            # https://www.alibabacloud.com/help/en/elastic-compute-service/latest/use-alibaba-cloud-linux-3-images-in-an-on-premises-environment
            rpm.RpmMirror('http://mirrors.aliyun.com/alinux/', 'os/' + arch + '/', v3_only),
            rpm.RpmMirror('http://mirrors.aliyun.com/alinux/', 'updates/' + arch + '/', v3_only),
            rpm.RpmMirror('http://mirrors.aliyun.com/alinux/', 'plus/' + arch + '/', v3_only),

        ]
        super(AliyunLinuxMirror, self).__init__(mirrors, arch)

    def to_driverkit_config(self, release, deps):
        for dep in deps:
            if dep.find("devel") != -1:
                return repo.DriverKitConfig(release, "alinux", dep)
