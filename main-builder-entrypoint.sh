#!/bin/bash

set -euo pipefail

usage()
{
	cat >&2 <<EOF
Usage:
	docker run --rm \\
		-v /var/run/docker.sock:/var/run/docker.sock \\
		IMAGE -P [-b BUILDER_IMAGE_PREFIX/] [-- BUILDER_OPTIONS...]

	docker run --rm \\
		-v /var/run/docker.sock:/var/run/docker.sock \\
		-v WORKSPACE:/workspace \\
		-v SYSDIG:/sysdig \\
		-v KERNELS:/kernels \\
		IMAGE -B [-b BUILDER_IMAGE_PREFIX/] [-- BUILDER_OPTIONS...]

	docker run --rm IMAGE -C -- DISTRIBUTION

	docker run --rm \\
		-v KERNELS:/kernels \\
		IMAGE -A [-- ARTIFACTORY_DOWNLOADER_OPTIONS...]

Required volumes:
	- /var/run/docker.sock for spawning build containers
	- WORKSPACE
		the main workspace, will be used to unpack kernel packages
		and run the actual build
	- SYSDIG
		the directory containing Sysdig sources in the version
		you wish to build
	- KERNELS
		the directory containing kernel packages (image, headers etc.)

Options:
	-B
		Build the probes

	-P
		Prepare the probe builder images ahead of time

	-b BUILDER_IMAGE_PREFIX/
		Use BUILDER_IMAGE_PREFIX/ as the prefix for all builder images.
		It should match the prefix used with the -P option below
		(in an earlier invocation)

	-A
		Download kernel packages from an Artifactory instance

	-C
		Run the kernel crawler to list available kernel packages
		for a particular distribution. Run without extra parameters
		to see the supported distributions.

	-d
		Enable debug (pass --debug to the probe builder)
EOF
	exit 1
}

check_docker_socket()
{
	if ! docker info &>/dev/null
	then
		echo "Docker socket not available" >&2
		echo >&2
		usage
	fi
}

build_probes()
{
	check_docker_socket
	cd /workspace
	probe_builder ${DEBUG_PREFIX} build -s /sysdig -b "$BUILDER_IMAGE_PREFIX" "$@" /kernels/*
}

prepare_builders()
{
	check_docker_socket
	for i in Dockerfile.* ; do docker build -t ${BUILDER_IMAGE_PREFIX}sysdig-probe-builder:${i#Dockerfile.} -f $i . ; done
}

download_from_artifactory()
{
	cd /kernels
	artifactory_download "$@"
}

crawl()
{
	probe_builder ${DEBUG_PREFIX} crawl "$@"
}

BUILDER_IMAGE_PREFIX=
DEBUG_PREFIX=
while getopts ":Ab:BCdP" opt
do
	case "$opt" in
		A)
			OP=download_from_artifactory
			;;
		b)
			BUILDER_IMAGE_PREFIX=$OPTARG
			;;
		B)
			OP=build
			;;
		C)
			OP=crawl
			;;
		d)
			DEBUG_PREFIX="--debug"
			;;
		P)
			OP=prepare
			;;
		\?)
			echo "Invalid option $OPTARG" >&2
			echo "Did you mean to pass it to the probe builder? Add -- before" >&2
			echo >&2
			usage
			;;
		:)
			echo "Option $OPTARG requires an argument" >&2
			echo >&2
			usage
			;;
	esac
done

shift $((OPTIND - 1))

case "${OP:-}" in
	download_from_artifactory)
		download_from_artifactory "$@"
		;;
	build)
		build_probes "$@"
		;;
	crawl)
		crawl "$@"
		;;
	prepare)
		prepare_builders
		;;
	*)
		usage
		;;
esac
