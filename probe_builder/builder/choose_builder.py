import os
import logging
import re

from ..version import Version

logger = logging.getLogger(__name__)

AUTOCONF_RE = re.compile('^#define CONFIG_GCC_VERSION ([0-9][0-9]?)([0-9][0-9])([0-9][0-9])$')
LINUX_COMPILER_RE = re.compile('^#define LINUX_COMPILER "gcc version ([0-9.]+)')
FEDORA_KERNEL_RE = re.compile(r'.*\.(fc[0-9]+)\..*Kernel Configuration$')


def get_kernel_distro_tag(kernel_dir):
    # Try to find a distro-specific builder based on the version
    # embedded in the header of autoconf.h
    # /*
    #  *
    #  * Automatically generated file; DO NOT EDIT.
    #  * Linux/x86_64 5.15.5-100.fc34.x86_64 Kernel Configuration
    #  *
    #  */
    try:
        logger.debug('checking {} for distro tag'.format(os.path.join(kernel_dir, "include/generated/autoconf.h")))
        with open(os.path.join(kernel_dir, "include/generated/autoconf.h")) as fp:
            for line in fp:
                m = FEDORA_KERNEL_RE.match(line)
                if m:
                    distro_tag = m.group(1)
                    return distro_tag
    except IOError:
        pass


def choose_distro_dockerfile(builder_source, _builder_distro, kernel_dir):
    distro_tag = get_kernel_distro_tag(kernel_dir)
    if distro_tag is None:
        return

    dockerfile = os.path.join(builder_source, 'Dockerfile.{}'.format(distro_tag))
    if os.path.exists(dockerfile):
        return dockerfile, distro_tag


def get_kernel_gcc_version(kernel_dir):
    # Try to find the gcc version used to build this particular kernel
    # Check CONFIG_GCC_VERSION=90201 in the kernel config first
    # as 5.8.0 seems to have a different format for the LINUX_COMPILER string
    try:
        logger.debug('checking {} for gcc version'.format(os.path.join(kernel_dir, "include/generated/autoconf.h")))
        with open(os.path.join(kernel_dir, "include/generated/autoconf.h")) as fp:
            for line in fp:
                m = AUTOCONF_RE.match(line)
                if m:
                    version = [int(m.group(1)), int(m.group(2)), int(m.group(3))]
                    return '.'.join(str(s) for s in version)
    except IOError:
        pass

    # then, try the LINUX_COMPILER macro, in two separate files
    try:
        logger.debug('checking {} for gcc version'.format(os.path.join(kernel_dir, "include/generated/compile.h")))
        with open(os.path.join(kernel_dir, "include/generated/compile.h")) as fp:
            for line in fp:
                m = LINUX_COMPILER_RE.match(line)
                if m:
                    return m.group(1)
    except IOError:
        pass

    # RHEL 6
    try:
        logger.debug('checking {} for gcc version'.format(os.path.join(kernel_dir, "include/compile.h")))
        with open(os.path.join(kernel_dir, "include/compile.h")) as fp:
            for line in fp:
                m = LINUX_COMPILER_RE.match(line)
                if m:
                    return m.group(1)
    except IOError:
        pass

    # ancient Ubuntu gets an ancient compiler
    return '4.8.0'


def choose_gcc_dockerfile(builder_source, builder_distro, kernel_dir):
    kernel_gcc = get_kernel_gcc_version(kernel_dir)
    # We don't really care about the compiler patch levels, only the major/minor version
    kernel_gcc = Version(kernel_gcc)

    # Choose the right gcc version from the ones we have available (as Docker images)
    # - if we have the exact minor version, use it
    # - if not, and there's a newer compiler version, use that
    #   (as close to the requested version as possible)
    # - if there are no newer compilers, use the newest one we have
    #   it will be older than the requested one but hopefully
    #   not by much
    #
    # This means we don't have to exactly follow all distro gcc versions
    # (indeed, we don't e.g. for AmazonLinux) but only need to add a new
    # Dockerfile when the latest kernel fails to build with our newest
    # gcc for that distro

    # The dockerfiles in question all look like .../Dockerfile.centos-gcc4.4
    # or similar. We want to pick the one that's closest to `kernel_gcc`
    # (exact match, slightly newer, slightly older, in that order of preference).
    # To do that, we iterate over the list of all available dockerfiles (i.e. gcc
    # versions) for a particular distribution in ascending version order (oldest->newest).
    # To get actual sorting by version numbers, we strip the common prefix first
    # and add it back after finding the best available version. What we're sorting is:
    #   4.4
    #   9.2
    #   10.0
    # and now we properly realize that gcc 10 is newer than 9.2, not older than 4.4
    prefix = 'Dockerfile.{}-gcc'.format(builder_distro)
    dockerfile_versions = [Version(f[len(prefix):]) for f in os.listdir(builder_source) if f.startswith(prefix)]
    dockerfile_versions.sort()
    logger.debug('available dockerfiles: {!r}'.format(dockerfile_versions))

    chosen = None
    for version in dockerfile_versions:
        chosen = version
        if version >= kernel_gcc:
            break

    dockerfile = prefix + str(chosen)
    tag = dockerfile.replace('Dockerfile.', '')
    return os.path.join(builder_source, dockerfile), tag


def choose_dockerfile(builder_source, builder_distro, kernel_dir):
    dockerfile_with_tag = choose_distro_dockerfile(builder_source, builder_distro, kernel_dir)
    if dockerfile_with_tag is not None:
        return dockerfile_with_tag

    return choose_gcc_dockerfile(builder_source, builder_distro, kernel_dir)
