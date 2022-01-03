#!/bin/sh

set -euo pipefail

usage() {
	cat >&2 <<EOF
Usage:
	$0 DISTRIBUTION KERNEL_PACKAGE OUTPUT_DIR
EOF
	exit 1
}

unpack_coreos_kernel()
{
	KERNEL_PACKAGE="$1"
	OUTPUT_DIR="$2"

	bzcat "$KERNEL_PACKAGE" > /tmp/container.img

	# mount developer container is a very stateful part of this script
	# the section between mount/unmounting should be kept very small
	# otherwise if something fails there are many inconsistencies that can happen
	OFFSET=$(sfdisk -J /tmp/container.img | jq '.partitiontable.sectorsize * .partitiontable.partitions[0].start')
	mount -o ro,loop,offset="$OFFSET" /tmp/container.img /mnt

	# Copy kernel headers
	cp -r /mnt/lib/modules "$OUTPUT_DIR"

	# Copy kernel config
	rm -f $OUTPUT_DIR/config*
	cp /mnt/usr/boot/config* $OUTPUT_DIR/

	# umount the developer container
	umount /mnt
}

unpack_rpm()
{
	KERNEL_PACKAGE="$1"
	OUTPUT_DIR="$2"

	rpm2cpio "$KERNEL_PACKAGE" | (cd "$OUTPUT_DIR" && cpio -idm)
}

case "$1" in
	coreos)
		unpack_coreos_kernel "$2" "$3"
		;;
	rpm)
		unpack_rpm "$2" "$3"
		;;
	*)
		echo "Unsupported distribution $1"
		exit 1
		;;
esac
