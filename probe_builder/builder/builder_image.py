import logging
import os

from .. import docker
from ..version import Version


logger = logging.getLogger(__name__)


def build(workspace, dockerfile, dockerfile_tag):
    image_name = '{}sysdig-probe-builder:{}'.format(workspace.image_prefix, dockerfile_tag)
    docker.build(image_name, dockerfile, workspace.builder_source)


def run(workspace, probe, kernel_dir, kernel_release,
        config_hash, container_name, image_name, args):
    volumes = [
        docker.DockerVolume(workspace.host_workspace(), '/build/probe', False),
        docker.DockerVolume(workspace.host_dir(probe.sysdig_dir), '/build/probe/sysdig', False),
    ]
    env = [
        docker.EnvVar('OUTPUT', '/build/probe/output'),
        docker.EnvVar('PROBE_NAME', probe.probe_name),
        docker.EnvVar('PROBE_VERSION', probe.probe_version),
        docker.EnvVar('PROBE_DEVICE_NAME', probe.probe_device_name),
        docker.EnvVar('KERNELDIR', kernel_dir.replace(workspace.workspace, '/build/probe/')),
        docker.EnvVar('KERNEL_RELEASE', kernel_release),
        docker.EnvVar('HASH', config_hash),
        docker.EnvVar('HASH_ORIG', config_hash)
    ]

    docker.run(image_name, volumes, args, env, name=container_name)


def probe_output_file(probe, kernel_release, config_hash, bpf):
    arch = os.uname()[4]
    if bpf:
        return '{}-bpf-{}-{}-{}-{}.o'.format(
            probe.probe_name, probe.probe_version, arch, kernel_release, config_hash
        )
    else:
        return '{}-{}-{}-{}-{}.ko'.format(
            probe.probe_name, probe.probe_version, arch, kernel_release, config_hash
        )


SKIPPED_KERNELS = [
    ("4.15.0-29-generic", "ea0aa038a6b9bdc4bb42152682bba6ce"),
    ("5.8.0-1023-aws", "3f7746be1bef4c3f68f5465d8453fa4d"),
]


def skip_build(probe, output_dir, kernel_release, config_hash, bpf):
    probe_file_name = probe_output_file(probe, kernel_release, config_hash, bpf)

    if os.path.exists(os.path.join(output_dir, probe_file_name)):
        return "Already built"

    if (kernel_release, config_hash) in SKIPPED_KERNELS:
        return "Unsupported kernel"
    if bpf:
        kernel_version = Version(kernel_release)
        if kernel_version < Version('4.14'):
            return 'Kernel {} too old to support eBPF (need at least 4.14)'.format(kernel_release)
