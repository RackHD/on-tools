#!/bin/bash

#
# This script is for build/push rackhd docker images.
# Environmental requirement:
#   1.docker service running and docker have already logged with Rackhd Dockerhub ID, 
#     cmd 'docker login', if not logged then can't push images to dockerhub
#   2.A sources.list to replace default sources.list of nodesource/wheezy:4.4.6 image(the root image which on-core pulled)
#     http://httpredir.debian.org/debiani(not stable for EMC network.) -> http://ftp.us.debian.org/debian
# Parameters:
#   ${1}, WORKDIR, default: ../../, a absolute where all repos are cloned
#   ${2}, DEVEL, default: false, a bool value indicate if is building on master branch

#when run this script locally use default value
WORKDIR=${1}
BASEDIR=$(cd $(dirname "$0");pwd)
WORKDIR=${WORKDIR:=$(dirname $(dirname $BASEDIR))}

DEVEL=${2}
DEVEL=${DEVEL:=false}

DEFAULT_VERSION=test

doBuild() {
    # List order is important, on-tasks image build is based on on-core image, 
    # on-http and on-taskgraph ard based on on-tasks image 
    # others are based on on-core image
    repos=$(echo "on-core on-syslog on-dhcp-proxy on-tftp on-wss on-statsd on-tasks on-taskgraph on-http")
    #Record all repo:tag for post-pushing
    repos_versions=""
    #For relpacing the unstable wheezy official source
    SOURCE_LIST=https://raw.githubusercontent.com/RackHD/on-tools/master/manifest-build-tools/docker_sources.list
    for repo in $repos;do
        if [ ! -d $repo ]; then
            echo "Repo directory of $repo does not exist"
            popd > /dev/null 2>&1
            exit 1
        fi
        pushd $repo
            PKG_VERSION=""
            if [ "$BUILD_LATEST" != true ]; then
                #use the provided version number if exists in .version
                PKG_VERSION=$(source ./.version && PKG_VERSION=${PKG_VERSION//\~/-} && echo $PKG_VERSION)
                VERSION=:${PKG_VERSION:=$DEFAULT_VERSION}
            fi
            echo "Building rackhd/$repo$VERSION"
            repos_versions=$repos_versions$repo$VERSION" "
            cp Dockerfile ../Dockerfile.bak
            if [ "$repo" != "on-core" ];then
                    # Use the new sources.list
                    sed -i "/^FROM/a RUN mv /etc/apt/sources.list /etc/apt/sources.list.bak\nCOPY $SOURCE_LIST /etc/apt/sources.list" Dockerfile
                    #Based on newly build upstream image to build
                    sed -i "/^FROM/ s/$/${PRE_VERSION}/" Dockerfile
                    # Recover the sources.list
                    sed -i -e "\$aRUN mv /etc/apt/sources.list.bak /etc/apt/sources.list" Dockerfile
                    docker build -t rackhd/$repo$VERSION .
            fi
            case $repo in
                "on-core")
                    docker build -t rackhd/$repo$VERSION .
                    PRE_VERSION=$VERSION
                    ;;
                "on-tasks")
                    PRE_VERSION=$VERSION
                    ;;
            esac 
            mv ../Dockerfile.bak Dockerfile
        popd
    done

    # Push all newly build images to Dockerhub
    for repo_version in $repos_versions;do
        echo "Pushing rackhd/$repo_version "
        docker push rackhd/$repo_version
    done
}

# Build begins
pushd $WORKDIR
doBuild
if [[ "$DEVEL" == true ]];then
    # latest tag is for master branch build.
    BUILD_LATEST=true
    doBuild
fi
popd
# Build ends