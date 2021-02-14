#!/bin/bash

# //Configurable parameters

ROOTDIR="/home/rpmbuilder"
WORKDIR="/home/rpmbuilder/work"
BUILD_DIR="${WORKDIR}/build"
GITLAB_CONFIG_FILE="${ROOTDIR}/gitlab_config.txt"
GITLAB_RSA_KEY="${ROOTDIR}/rpmbuilder.rsa"
SRPM_BUILD_LOG="${WORKDIR}/srpm_build.log"
RPM_BUILD_LOG="${WORKDIR}/rpm_build.log"

# /* END BLOCK */

# // No need to verify arguments here - they've already been sanitized by upper script.

# // passed args

GITURL=${1} # Git URL for downloading sources. Can be either https or ssh endpoint depending on method of downloading.
GITBRANCH=${2} # Git branch/tag of the program that has to be built. Master by default. 
PKGVERSION=${3} # Version of the package. See https://asgardahost.ru/library/syseng-guide/00-rules-and-conventions-while-working-with-software-and-tools/4-packaging for naming details. 
GET_SRC_METHOD=${4} # Method of getting sources
SPECFILE=${WORKDIR}/${5} # SPECFILE
RELEASE_VER=${6} # A release version. Usually just a UNIX timestamp if other is not specified explicitly in .gitlab-ci.yml

# /* END BLOCK */

# If rpmbuilder.rsa is included into docker image and git_clone method was chosen for getting sources - use native git clone command for building. Otherwise use Gitlab API.

if [ -e ${GITLAB_RSA_KEY} -a "x${GET_SRC_METHOD}" == "xgit_clone" ] ; then

    cp -v ${ROOTDIR}/${5} ${SPECFILE} # copy SPEC file into workdir. 
    eval $(ssh-agent)
    ssh-add ${GITLAB_RSA_KEY}
    ssh-add -l
    echo "${GITURL} ${GITBRANCH} ${PKGVERSION} ${RELEASE_VER} ${SPECFILE}"
    echo "Starting build using git clone..."

elif [ -e ${GITLAB_CONFIG_FILE} ] ; then # We have to pass config file containing token for access to Gitlab API
    
    echo "${GITURL} ${GITBRANCH} ${PKGVERSION} ${RELEASE_VER} ${SPECFILE}"
    echo "Starting build using prepared sources downloaded via Gitlab API..."

else

    echo "Unable to access Gitlab. Please check."
    exit 1

fi

#### /* END BLOCK */ ####

# // Prepare .src.rpm for the following yum-builddep command

rpmbuild -bs --nodeps --define "get_src_method ${GET_SRC_METHOD}" --define "config_file ${GITLAB_CONFIG_FILE}" --define "source_url ${GITURL}" --define "version ${PKGVERSION}" --define "branch_or_tag ${GITBRANCH}" --define "builddir ${BUILD_DIR}" --define "release_ver ${RELEASE_VER}" "${SPECFILE}" > ${SRPM_BUILD_LOG} 2>&1
RC=$?

if [ ${RC} -ne 0 ]; then
    echo "Unable to build SRPM file from ${SPECFILE}. Parameters were: ${GITURL} ${PKGVERSION} ${GITBRANCH} ${RELEASE_VER}. Please check logz"
    exit 2
else
    SRPM=$( cat ${SRPM_BUILD_LOG} | grep "Wrote: " | grep "src.rpm" | awk '{ print $NF }' )
    echo "SRPM build succeeded: ${SRPM}. Starting builddep installation"
fi

# /* END BLOCK */

# // Building dependencies

sudo yum-builddep -y "${SRPM}"
if [ $? -ne 0 ]; then
    echo "Failed to install BuildDeps from ${SPECFILE}. Parameters were: ${GITURL} ${PKGVERSION} ${GITBRANCH} ${RELEASE_VER}. Please check logz"
    exit 3
fi

# /* END BLOCK */

# // Build RPM itself.

rpmbuild -bb --define "get_src_method ${GET_SRC_METHOD}" --define "config_file ${GITLAB_CONFIG_FILE}" --define "source_url ${GITURL}" --define "version ${PKGVERSION}" --define "branch_or_tag ${GITBRANCH}" --define "builddir ${BUILD_DIR}" --define "release_ver ${RELEASE_VER}" "${SPECFILE}" > ${RPM_BUILD_LOG} 2>&1
RC=$?

if [ ${RC} -ne 0 ]; then

    echo "Failed to build RPM from ${SPECFILE}. Parameters were: ${GITURL} ${PKGVERSION} ${GITBRANCH} ${RELEASE_VER}. Please check logz"
    exit 4

else
    
    RESULT_RPMS=$( cat ${RPM_BUILD_LOG} | grep "Wrote: " | egrep '\.rpm$' | awk '{ print $NF }' | xargs )
    echo "Successfully built ${RESULT_RPMS}."

fi

# /* END BLOCK */

mkdir  ${WORKDIR}/RPM
for pkg in `echo ${RESULT_RPMS} | tr " " "\n"` ; do
    cp ${pkg} ${WORKDIR}/RPM
done

exit 0

