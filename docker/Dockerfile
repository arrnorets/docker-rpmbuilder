FROM centos:7

MAINTAINER Roman Chukov <r.chukov@asgardahost.ru>

RUN yum -y install epel-release \
    && yum -y update \
    && yum -y install yum-utils rpm-build sudo \
    && yum -y install git

RUN mkdir -p /home/rpmbuilder/.ssh \
    && chmod 0700 /home/rpmbuilder/.ssh 

COPY known_hosts /root/.ssh/known_hosts
COPY sudoers /etc/sudoers
RUN chmod 440 /etc/sudoers && \
    chown root:root /etc/sudoers

COPY rpmbuild.sh /home/rpmbuilder/rpmbuild.sh
RUN chmod 755 /home/rpmbuilder/rpmbuild.sh

RUN mkdir -p /home/rpmbuilder/work /rpmbuild
VOLUME [ "/home/rpmbuilder/work" ]

RUN groupadd -g 988 rpmbuilder && \
    useradd -u 991 -g 988 -s /home/rpmbuilder rpmbuilder && \
    chown -R rpmbuilder:rpmbuilder /home/rpmbuilder /rpmbuild

USER rpmbuilder

# Set the working directory to app home directory
WORKDIR /home/rpmbuilder

ENTRYPOINT [ "/home/rpmbuilder/rpmbuild.sh" ]

