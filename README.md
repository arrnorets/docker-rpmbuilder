# Table of contents
1. [General description](#1-general-description)
2. [For which distros can I build my RPM packages using this tool ?](#2-for-which-distros-can-i-build-my-rpm-packages-using-this-tool-?)
3. [Compatibility](#3-compatibility)
4. [Requirements for installation](#4-requirements-for-installation)
5. [Requirements to project in Gitlab](#5-requirements-to-project-in-gitlab)
6. [Example of usage with .gitlab-ci.yml](#6-example-of-usage-with-.gitlab-ci.yml)

# 1. General description.
Docker-rpmbuilder is a set of utilities that provides a (semi)automated RPM packages building process using Gitlab. The main aim is to provide an automation for RPM packages building in a context of Gitlab pipelines provided by .gitlab-ci.yml, but scripts can also be executed manually in order either to buid package or to sign it. As it foow from its name, scripts are using special docker image that actually does all the stuff.

# 2. For which distros can I build my RPM packages using this tool ?
At the moment you can build packages for any RPM-based distributive that use rpm-build and yum-utils for packaging process, i.e. at least CentOS/RHEL 6,7,8 are supported. For RPM-based systems that use another package backends rpmbuilder.sh script modification is required as well as corresponding Dockerfile must be provided.

# 3. Compatibility
This set of utilities can be executed on any platform that supports Python 3 and Docker. 

# 4. Requirements for installation
  4.1 _musthave_ requirements:
    
    - Docker ;
    - Python 3.6 or higher version ;
    - User with uid 991 and gid 988 must be created. This is the actual effective uid for running building stuff. If you have Gitlab runner already installed on your box then most probably this item is already satisfied as it creates gitlab-runner user with required attributes.
    - A docker image of the target RPM-based system must be pulled into the builder box. In the _docker_ directory there is a Dockerfile for CentOS 7 x86_64 image.
    - Files from _conf_ dirctory must be placed under /etc and configured with valid Gitlab token that has permissions to read repositories and use its API.

  4.2. optional requirements ( for package signing procedure ):
    
    - pexpect module for Python 3 and gpg utility ( optional, if you want to sign your packages after building using RPM_Addsign.py script );
    - Valid GPG key must be configured in advance for user who executes RPM_Addsign.py script.

# 5. Requirements to project in Gitlab
Below is the minimall structure of the project that is required for buiding tool:

```bash
12:35:44 ~/work/syseng/Asgardahost-work/development/asgardahost-rpm_repository [master|✔]
syseng@5540b4c95ea6 $ tree
.
├── asgardahost.repo
├── BUILD_DEPS_REPO
│   └── build-deps.repo
├── README.md
└── SPEC
    └── asgardahost-rpm_repository.spec
```

- _BUILD_DEPS_REPO_ contains file _build-deps.repo_ that describes additional repositories that are necessary to buid the package. It can be left empty if no one is needeed, but at lest the empty file is required.
- _SPEC_ directory contains the .spec file. _The name of the .spec fil must be exactly the same as repository name, as buiding script relies on it._ 
- If you are using sources from the same project in Gitlab ( file _asgardahost.repo_ in our example ), .spec file must contain a special %prep block with two ogligatory if-else clauses that define a method of sources downloading and its preparation ( please see example below ). I want to underline that using Gitlab API is much more preferrable way of doing it, however, direct repository clone is also supproted, though it requires to configure an accss to Gitlab via ssh key and pass it to _pkg_Builder.py_ script ( please see usage of the script ). Also in case of direct clone _known_hosts_ file in _docker_ directory must contain the fingerprint of your Gitlab server.

.spec file content:
```
#
# spec file for asgardahost-rpm_repository
#

Name:           asgardahost-rpm_repository
Version:        %{version}
Release:        1%{?dist}
Url:            https://asgardahost.ru
Summary:        A package that provides a configuration of Asgardahost repository
License:        GPL
Group:          Misc
# Source0:      We always get sources from Gitlab repo

BuildArch:      noarch
BuildRoot:      %(mktemp -ud %{_tmppath}/%{name}-%{version}-XXXXXX)

Provides:       asgardahost-rpm_repository

Requires:       yum

Prefix:		/etc/yum.repos.d

%description
This packages configures Asgardahost RPM repository

%prep
%if %{get_src_method} == "git_clone"
    rm -fr %{builddir}
    mkdir %{builddir}
    cd %{builddir}
    git clone %{source_url} %{name}
    cd %{name}
    git checkout %{branch_or_tag}
%else
    rm -fr %{builddir}
    mkdir %{builddir}
    cd %{builddir}
    curl -o archive.tar.gz -K %{config_file} "%{source_url}/archive.tar.gz?sha=%{branch_or_tag}"
    tar -xvzf archive.tar.gz
    rm -f archive.tar.gz
    SRC_DIR=`ls`
    mv ${SRC_DIR} %{name}
    cd %{name}
%endif

%build

%install
mkdir -p ${RPM_BUILD_ROOT}/%{prefix}
install -m 755 %{builddir}/%{name}/asgardahost.repo ${RPM_BUILD_ROOT}/%{prefix}/asgardahost.repo

%files
%defattr(-,root,root,-)
%{prefix}/asgardahost.repo

%post

%clean
rm -fr ${RPM_BUILD_ROOT}
rm -fr %{builddir}

%changelog
* Sun Feb 14 2021 Roman A. Chukov <r.chukov@asgardahost.ru>
- Bumping up to ver 2.0. Fixed URL of website.

* Sun Jun 30 2019 Roman A. Chukov <r.chukov@asgardahost.ru>
- An initial version 1.0
```

# 6. Example of usage with .gitlab-ci.yml
- _.gitab-ci.yml_ :

```yaml
---
variables:
  GIT_STRATEGY: none
  CI_GITLAB_SERVER: "https://gitlab.asgardahost.ru"

build:
  variables:
    CI_IS_PKG_VERSION_MANAGED: "yes"
    CI_PKG_VERSION: "2.0"
    CI_BUILDER_IMAGE: "registry.asgardahost.ru:4444/docker/asg_registry/public/rpmbuilder_centos7:amd64_1.5"
  script:
    - pkg_Builder.sh
```
- _Here are parts of pkg_Builder.sh script that explain using of docker-rpmbuilder tools_ :
```bash

CURRENT_TIME=$( date +%s )
REPOSITORY_NAME=$( echo "${CI_PROJECT_DIR}" | awk -F '/' '{ print $NF }' )

# /* Define what branch or tag we have to build from */

Outcome: PKG_BRANCH_TAG=""

# /* END BLOCK */

# /* Optionally manage pkg_version and release via .gitlab-ci.yml 
# Corresponding setting myst be enabled for that. */

Outcome: PKG_VERSION && RELEASE_VER

# /* END BLOCK */

# /* Run the building and check if build was succeeded */

/opt/rpmbuilder/utils/pkg_Builder.py --current_time "${CURRENT_TIME}" --gitlab_url "${CI_GITLAB_SERVER}" --repository_name "${REPOSITORY_NAME}" --build_container_image "${CI_BUILDER_IMAGE}" --pkg_branch "${PKG_BRANCH_TAG}" --pkg_version "${PKG_VERSION}" --release_ver "${RELEASE_VER}" --get_src_method "gitlab_api" --curl_token_file /etc/rpmbuilder.conf
RETCODE=$?

if [ ${RETCODE} -ne 0 ] ; then
    echo "Failed to build package from ${REPOSITORY_NAME} of ${PKG_BRANCH_TAG} version ${PKG_VERSION}"
    exit 1
fi

# /* END BLOCK */

# /* Sign the packages */

/opt/rpmbuilder/utils/RPM_Addsign.py /home/gitlab-runner/builds/${REPOSITORY_NAME}-${PKG_BRANCH_TAG}-${CURRENT_TIME}/RPM
if [ $? -ne 0 ] ; then
    echo "Failed to sign packages in /home/gitlab-runner/builds/${REPOSITORY_NAME}-${PKG_BRANCH_TAG}-${CURRENT_TIME} dir from ${REPOSITORY_NAME} of ${PKG_BRANCH_TAG} version ${PKG_VERSION}"
    exit 2
fi

# /* END BLOCK */
```

- _Here is the result_ :
```bash
Running with gitlab-runner 13.4.0 (4e1f20da)
  on katello.asgardahost.ru zbba1cPp
  Preparing the "shell" executor
  Using Shell executor...
  Preparing environment
  Running on katello.asgardahost.ru...
  Getting source from Git repository
  Skipping Git repository setup
  Skipping Git checkout
  Skipping Git submodules setup
  Executing "step_script" stage of the job script
  $ pkg_Builder.sh
  We are starting with the followings args: gitlab_api | https://gitlab.asgardahost.ru | asgardahost-rpm_repository            | registry.asgardahost.ru:4444/docker/asg_registry/public/rpmbuilder_centos7:amd64_1.5 | master | 2.0
  Repo information retrieved: OK.
  200
  Downloading SPEC file... Ok.
  200
  Downloading repo file for building deps... Ok.
  200
  Downloading archive... Ok.
  Starting to build package. Please be patient.
  ======
  Executing command ['docker', 'run', '-i', '--name', 'asgardahost-rpm_repository-master-1613298066', '--user', '991:988', '--mount', 'type=bind,source=/etc/rpmbuilder.conf,target=/home/rpmbuilder/gitlab_config.txt', '--mount', 'type=bind,source=/home/gitlab-runner/builds/asgardahost-rpm_repository-master-1613298066/build-deps.repo,target=/etc/yum.repos.d/build-deps.repo', '-v', '/home/gitlab-runner/builds/asgardahost-rpm_repository-master-1613298066:/home/rpmbuilder/work', 'registry.asgardahost.ru:4444/docker/asg_registry/public/rpmbuilder_centos7:amd64_1.5', 'https://gitlab.asgardahost.ru/api/v4/projects/44/repository', 'master', '2.0', 'gitlab_api', 'asgardahost-rpm_repository.spec', '1'] .
  Build command finished with retcode 0 and message b'https://gitlab.asgardahost.ru/api/v4/projects/44/repository master 2.0 1 /home/rpmbuilder/work/asgardahost-rpm_repository.spec\nStarting build using prepared sources downloaded via Gitlab API...\nSRPM build succeeded: /home/rpmbuilder/rpmbuild/SRPMS/asgardahost-rpm_repository-2.0-1.el7.src.rpm. Starting builddep installation\nLoaded plugins: fastestmirror, ovl\nEnabling base-source repository\nEnabling epel-source repository\nEnabling extras-source repository\nEnabling updates-source repository\nDetermining fastest mirrors\n * base: ftp.wrz.de\n * epel: mirror.speedpartner.de\n * epel-source: mirror.speedpartner.de\n * extras: ftp.rz.uni-frankfurt.de\n * updates: mirror.23media.com\nChecking for new repos for mirrors\nGetting requirements for asgardahost-rpm_repository-2.0-1.el7.src\nNo uninstalled build requires\nSuccessfully built /home/rpmbuilder/rpmbuild/RPMS/noarch/asgardahost-rpm_repository-2.0-1.el7.noarch.rpm.'

  =====Successful exiting
  The build directory is: /home/gitlab-runner/builds/asgardahost-rpm_repository-master-1613298066
```

- _Let's check our package_:
```bash
$ rpm -qip asgardahost-rpm_repository-2.0-1.el7.noarch.rpm
Name        : asgardahost-rpm_repository
Version     : 2.0
Release     : 1.el7
Architecture: noarch
Install Date: (not installed)
Group       : Misc
Size        : 546
License     : GPL
Signature   : RSA/SHA256, Вс 14 фев 2021 13:21:46, Key ID 609b3b1d62b464ec
Source RPM  : asgardahost-rpm_repository-2.0-1.el7.src.rpm
Build Date  : Вс 14 фев 2021 13:21:44
Build Host  : 5dcaf4fda939
Relocations : /etc/yum.repos.d
URL         : https://asgardahost.ru
Summary     : A package that provides a configuration of Asgardahost repository
Description :
This packages configures Asgardahost RPM repository

$ rpm -qlp asgardahost-rpm_repository-2.0-1.el7.noarch.rpm 
/etc/yum.repos.d/asgardahost.repo
```

