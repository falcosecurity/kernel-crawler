import errno
import logging

from .. import docker, spawn
import os

logger = logging.getLogger(__name__)


HAVE_TOOLKIT = False


def toolkit_image(image_prefix):
    return '{}sysdig-probe-builder:toolkit'.format(image_prefix)


def build_toolkit(workspace):
    global HAVE_TOOLKIT
    if HAVE_TOOLKIT:
        return
    image = toolkit_image(workspace.image_prefix)
    dockerfile = os.path.join(workspace.builder_source, 'Dockerfile.toolkit')
    docker.build(image, dockerfile, workspace.builder_source)
    HAVE_TOOLKIT = True


def unpack_rpm(workspace, rpm_file, target_dir, marker):
    if marker is not None and os.path.exists(marker):
        logger.info('{} already exists, not unpacking {}'.format(marker, rpm_file))
        return

    rpm_file = os.path.abspath(rpm_file)
    target_dir = os.path.abspath(target_dir)

    if not workspace.in_docker():
        build_toolkit(workspace)
        volumes = [
            docker.DockerVolume(rpm_file, rpm_file, True),
            docker.DockerVolume(target_dir, target_dir, False),
        ]
        docker.run(toolkit_image(workspace.image_prefix), volumes, ['rpm', rpm_file, target_dir], [])
    else:
        try:
            os.makedirs(target_dir, 0o755)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
        spawn.pipe(["/builder/toolkit-entrypoint.sh", "rpm", rpm_file, target_dir])

    if marker is not None:
        with open(marker, 'w') as marker_fp:
            marker_fp.write('\n')


def unpack_deb(workspace, deb_file, target_dir, marker):
    if marker is not None and os.path.exists(marker):
        logger.info('{} already exists, not unpacking {}'.format(marker, deb_file))
        return

    deb_file = os.path.abspath(deb_file)
    target_dir = os.path.abspath(target_dir)

    deb_file = workspace.host_dir(deb_file)
    target_dir = workspace.host_dir(target_dir)

    if deb_file is None:
        raise ValueError('Package {} not within workspace {}'.format(deb_file, workspace.workspace))

    if target_dir is None:
        raise ValueError('Target directory {} not within workspace {}'.format(target_dir, workspace.workspace))

    volumes = [
        docker.DockerVolume(deb_file, deb_file, True),
        docker.DockerVolume(target_dir, target_dir, False),
    ]
    docker.run('ubuntu:latest', volumes, ['dpkg', '-x', deb_file, target_dir], [])

    if marker is not None:
        with open(marker, 'w') as marker_fp:
            marker_fp.write('\n')
