#!/bin/bash

# install_wsl2_kernel_headers
# Install kernel headers for WSL2 kernel version.
#
# Usage:
#  % sudo bash
#  # install_wsl2_kernel_headers
#  OR
#  # KERNEL_BUILD_NUM_JOBS=8 install_wsl2_kernel_headers
#
# Steps:
# 1) Confirm caller is running as root, needed for permission to write to
#    /usr/src and /lib/modules
# 2) Verify that kernel version is of the expected format, *-microsoft-standard-WSL2
# 3) Form Linux kernel branch name
# 4) Check to see if /lib/modules/<kernel-version> directory already exists;
#    if so, does nothing else
# 5) Remove any existing kernel source tree, /usr/src/linux-src-x.x.x-sysdig, since that
#    tree is in an unknown state
# 6) Retrieve kernel source tree from github WSL2-Linux-Kernel, into
#    /usr/src/linux-src-x.x.x-sysdig
# 7) Install Microsoft-provided config file.
# 8) Build kernel, honoring environment variable KERNEL_BUILD_NUM_JOBS if provided.
# 9) Install kernel headers into /lib/modules/<kernel-version>
# 10) Validate /lib/modules/<kernel-version> directory now present
# 11) Remove unneeded files from kernel source tree, to save space


#==========================================================================================
# 1) Confirm caller is running as root, needed for permission to write to
#    /usr/src and /lib/modules
#==========================================================================================
if [ "${EUID}" != "0" ]
then
    echo Error: Must execute as root, for access to /usr/src and /lib/modules
    exit 1
fi


#==========================================================================================
# 2) Verify that kernel version is of the expected format, *-microsoft-standard-WSL2
#==========================================================================================
MICROSOFT_KERNEL_RELEASE_SUFFIX=-microsoft-standard-WSL2
UNAME_KERNEL_RELEASE=`uname -r`

if [[ ${UNAME_KERNEL_RELEASE} != *${MICROSOFT_KERNEL_RELEASE_SUFFIX} ]]
then
    echo Error: Unsupported kernel version ${UNAME_KERNEL_RELEASE}
    echo Only \*${MICROSOFT_KERNEL_RELEASE_SUFFIX} versions supported
    exit 1
fi


#==========================================================================================
# 3) Form Linux kernel branch name
#==========================================================================================
KERNEL_VERSION_NUMBER=`echo ${UNAME_KERNEL_RELEASE} | sed "s/${MICROSOFT_KERNEL_RELEASE_SUFFIX}$//"`

if [[ ${KERNEL_VERSION_NUMBER} == *${UNAME_KERNEL_RELEASE} || ${KERNEL_VERSION_NUMBER} == "" ]]
then
    echo Error: Parsing kernel version number from ${UNAME_KERNEL_RELEASE} failed
    exit 1
fi

echo Supported kernel version ${UNAME_KERNEL_RELEASE}

LINUX_BRANCH=linux-msft-${KERNEL_VERSION_NUMBER}
echo LINUX_BRANCH=${LINUX_BRANCH}
echo


#==========================================================================================
# 4) Check to see if /lib/modules/<kernel-version> directory already exists;
#    if so, does nothing else
#==========================================================================================
LIB_MODULES_DIR=/lib/modules/${UNAME_KERNEL_RELEASE}
echo LIB_MODULES_DIR=${LIB_MODULES_DIR}

if [ -d ${LIB_MODULES_DIR} ]
then
    echo Kernel modules directory $LIB_MODULES_DIR already exists
    echo Performing no work.
    exit 0
fi


#==========================================================================================
# 5) Remove any existing kernel source tree, /usr/src/linux-src-x.x.x-sysdig, since that
#    tree is in an unknown state
#==========================================================================================
LINUX_SRC_DIR=/usr/src/${LINUX_BRANCH}-sysdig
if [ -d ${LINUX_SRC_DIR} ]
then
    echo Removing existing directory ${LINUX_SRC_DIR}
    CMD="rm -rf ${LINUX_SRC_DIR}"  # NOTE: rm -rf is dangerous; ONLY remove explicitly named directory
    echo ${CMD}
    eval ${CMD}

    if [ "$?" != "0" ]
    then
        echo Error: rm failed
        exit 1
    fi

    echo
fi


#==========================================================================================
# 6) Retrieve kernel source tree from github WSL2-Linux-Kernel, into
#    /usr/src/linux-src-x.x.x-sysdig
#==========================================================================================
echo Retrieving kernel source from github WSL2-Linux-Kernel, tag ${LINUX_BRANCH}, into ${LINUX_SRC_DIR}/${LINUX_SRC_TARFILE}

CMD="mkdir -p ${LINUX_SRC_DIR}"
echo ${CMD}
eval ${CMD}
if [ "$?" != "0" ]
then
    echo Error: mkdir failed
    exit 1
fi

LINUX_SRC_TARFILE=${LINUX_BRANCH}.tar.gz
CMD="curl -L https://github.com/microsoft/WSL2-Linux-Kernel/archive/refs/tags/${LINUX_BRANCH}.tar.gz --output ${LINUX_SRC_DIR}/${LINUX_SRC_TARFILE}"
echo ${CMD}
eval ${CMD}

if [ "$?" != "0" ]
then
    echo Error: curl failed
    exit 1
fi

echo Extracting kernel source from ${LINUX_SRC_TARFILE}
cd ${LINUX_SRC_DIR}
CMD="tar xf ${LINUX_BRANCH}.tar.gz --strip-components 1"
echo ${CMD}
eval ${CMD}

if [ "$?" != "0" ]
then
    echo Error: tar xf failed
    exit 1
fi

echo


#==========================================================================================
# 7) Install Microsoft-provided config file.
#==========================================================================================
echo
echo Installing Microsoft kernel config file
cd ${LINUX_SRC_DIR}
if [ ! -f Microsoft/config-wsl ]
then
    echo Error: Microsoft/config-wsl file not found in ${LINUX_SRC_DIR}
    exit 1
fi
CMD="cp Microsoft/config-wsl ./.config"
echo ${CMD}
eval ${CMD}

if [ "$?" != "0" ]
then
    echo Error: cp failed
    exit 1
fi

echo


#==========================================================================================
# 8) Build kernel, honoring environment variable KERNEL_BUILD_NUM_JOBS if provided.
#==========================================================================================
echo Building kernel

cd ${LINUX_SRC_DIR}
if [ "${KERNEL_BUILD_NUM_JOBS}" == "" ]
then
    CMD="make LOCALVERSION="
    echo ${CMD}
    eval ${CMD}
else
    echo Using environment variable KERNEL_BUILD_NUM_JOBS=${KERNEL_BUILD_NUM_JOBS}
    CMD="make -j $KERNEL_BUILD_NUM_JOBS LOCALVERSION="
    echo ${CMD}
    eval ${CMD}
fi

if [ "$?" != "0" ]
then
    echo Error: Kernel build failed
    exit 1
fi

echo


#==========================================================================================
# 9) Install kernel headers into /lib/modules/<kernel-version>
#==========================================================================================
echo Installing kernel headers
cd ${LINUX_SRC_DIR}
CMD="make modules_install"
echo ${CMD}
eval ${CMD}
if [ "$?" != "0" ]
then
    echo Error: make failed
    exit 1
fi

echo


#==========================================================================================
# 10) Validate /lib/modules/<kernel-version> directory now present
#==========================================================================================
if [ ! -d ${LIB_MODULES_DIR} ]
then
    echo Error: Kernel modules directory ${LIB_MODULES_DIR} still not present after modules_install
    exit 1
fi


#==========================================================================================
# 11) Remove unneeded files from kernel source tree, to save space
#==========================================================================================
echo Reclaiming space

echo Removing ${LINUX_BRANCH}.tar.gz
cd ${LINUX_SRC_DIR}
CMD="rm -f ${LINUX_BRANCH}.tar.gz"
echo ${CMD}
eval ${CMD}

if [ "$?" != "0" ]
then
    echo Error: rm failed
    exit 1
fi

CMD="make clean"
cd ${LINUX_SRC_DIR}
echo ${CMD}
eval ${CMD}
if [ "$?" != "0" ]
then
    echo Error: make failed
    exit 1
fi

echo Removing C files
CMD="find ${LINUX_SRC_DIR} -name '*.c' -print | xargs rm"
echo ${CMD}
eval ${CMD}

cd ${LINUX_SRC_DIR}
SUBDIRS="`echo [a-z]* | sed 's/arch//' | sed 's/include//'`"
if [ "$SUBDIRS" != "" ]
then
    echo Removing unneeded H files
    CMD="find $SUBDIRS -name '*.h' -print | xargs rm"
    echo ${CMD}
    eval ${CMD}
fi

echo Removing ASM files
CMD="find ${LINUX_SRC_DIR} -name '*.S' -print -o -name '*.asm' -print | xargs rm"
echo ${CMD}
eval ${CMD}

echo Removing PY files
CMD="find ${LINUX_SRC_DIR} -name '*.py' -print | xargs rm"
echo ${CMD}
eval ${CMD}

echo Removing JSON files
CMD="find ${LINUX_SRC_DIR} -name '*.json' -print | xargs rm"
echo ${CMD}
eval ${CMD}

echo Removing Documentation
CMD="find ${LINUX_SRC_DIR} -name 'Documentation' -print | xargs rm -r"
echo ${CMD}
eval ${CMD}

echo


echo Kernel modules installed into $LIB_MODULES_DIR
exit 0
