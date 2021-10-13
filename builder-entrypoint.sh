#!/bin/bash

# required env vars:
# HASH
# HASH_ORIG
# KERNELDIR
# KERNEL_RELEASE
# OUTPUT
# PROBE_DEVICE_NAME
# PROBE_NAME
# PROBE_VERSION

set -euo pipefail

ARCH=$(uname -m)

build_kmod() {
	if [[ -f "${KERNELDIR}/scripts/gcc-plugins/stackleak_plugin.so" ]]; then
		echo "Rebuilding gcc plugins for ${KERNELDIR}"
		(cd "${KERNELDIR}" && make gcc-plugins)
	fi

	echo Building $PROBE_NAME-$PROBE_VERSION-$ARCH-$KERNEL_RELEASE-$HASH.ko

	mkdir -p /build/sysdig
	cd /build/sysdig

	cmake -DCMAKE_BUILD_TYPE=Release -DPROBE_NAME=$PROBE_NAME -DPROBE_VERSION=$PROBE_VERSION -DPROBE_DEVICE_NAME=$PROBE_DEVICE_NAME -DCREATE_TEST_TARGETS=OFF /build/probe/sysdig
	make driver
	strip -g driver/$PROBE_NAME.ko

	KO_VERSION=$(/sbin/modinfo driver/$PROBE_NAME.ko | grep vermagic | tr -s " " | cut -d " " -f 2)
	if [ "$KO_VERSION" != "$KERNEL_RELEASE" ]; then
		echo "Corrupted probe, KO_VERSION " $KO_VERSION ", KERNEL_RELEASE " $KERNEL_RELEASE
		exit 1
	fi

	cp driver/$PROBE_NAME.ko $OUTPUT/$PROBE_NAME-$PROBE_VERSION-$ARCH-$KERNEL_RELEASE-$HASH.ko
	cp driver/$PROBE_NAME.ko $OUTPUT/$PROBE_NAME-$PROBE_VERSION-$ARCH-$KERNEL_RELEASE-$HASH_ORIG.ko
}


build_bpf() {
	if ! type -p clang > /dev/null
	then
		echo "clang not available, not building eBPF probe $PROBE_NAME-bpf-$PROBE_VERSION-$ARCH-$KERNEL_RELEASE-$HASH.o"
	else
		echo "Building eBPF probe $PROBE_NAME-bpf-$PROBE_VERSION-$ARCH-$KERNEL_RELEASE-$HASH.o"
		make -C /build/probe/sysdig/driver/bpf clean all
		cp /build/probe/sysdig/driver/bpf/probe.o $OUTPUT/$PROBE_NAME-bpf-$PROBE_VERSION-$ARCH-$KERNEL_RELEASE-$HASH.o
	fi
}

case "${1:-}" in
	bpf) build_bpf;;
	"") build_kmod;;
	*) exit 1;;
esac
