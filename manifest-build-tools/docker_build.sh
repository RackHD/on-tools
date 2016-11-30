#!/bin/bash 
set -e

#
# This script is for build/push rackhd docker images.
# Environmental requirement:
#   1.A sources.list to replace default sources.list of nodesource/wheezy:4.4.6 image(the root image which on-core pulled)
#     http://httpredir.debian.org/debiani(not stable for EMC network.) -> http://ftp.us.debian.org/debian
# Parameters:
#   ${1}, WORKDIR, default: ../../, a absolute where all repos are cloned
#   ${2}, IS_OFFICIAL_RELEASE, default: false, a bool value indicates if is building release


#when run this script locally use default value
WORKDIR=${1}
BASEDIR=$(cd $(dirname "$0");pwd)
WORKDIR=${WORKDIR:=$(dirname $(dirname $BASEDIR))}

IS_OFFICIAL_RELEASE=${2}
IS_OFFICIAL_RELEASE=${IS_OFFICIAL_RELEASE:=false}

tagCalculate() {
    repo=$1
    #Get package version from debian/changelog
    if [ -f "debian/changelog" ]; then
        CHANGELOG_VERSION=$(dpkg-parsechangelog --show-field Version)
    elif [ -f "debianstatic/$repo/changelog" ]; then
        cp -rf debianstatic/$repo ./debian
        CHANGELOG_VERSION=$(dpkg-parsechangelog --show-field Version)
        rm -rf debian
    else
        CHANGELOG_VERSION=$RACKHD_CHANGELOG_VERSION
    fi
    
    #generate real TAG
    if [ "$IS_OFFICIAL_RELEASE" == "true" ]; then
        PKG_TAG="$CHANGELOG_VERSION"
    else
        GIT_COMMIT_DATE=$(git show -s --pretty="format:%ci")
        DATE_STRING="$(date -d "$GIT_COMMIT_DATE" -u +"%Y%m%d%H%M%SZ")UTC"
        GIT_COMMIT_HASH=$(git show -s --pretty="format:%h")
        PKG_TAG="$CHANGELOG_VERSION-$DATE_STRING-$GIT_COMMIT_HASH"
    fi
}

doBuild() {
    # List order is important, on-tasks image build is based on on-core image, 
    # on-http and on-taskgraph ard based on on-tasks image 
    # others are based on on-core image
    repos=$(echo "on-core on-syslog on-dhcp-proxy on-tftp on-wss on-statsd on-tasks on-taskgraph on-http")
    #Record all repo:tag for post-pushing
    repos_tags=""
    #Set an empty TAG before each build
    TAG=""
    #For relpacing the unstable wheezy official source
    SOURCE_LIST=https://raw.githubusercontent.com/RackHD/on-tools/master/manifest-build-tools/docker_sources.list
    for repo in $repos;do
        if [ ! -d $repo ]; then
            echo "Repo directory of $repo does not exist"
            popd > /dev/null 2>&1
            exit 1
        fi
        pushd $repo
            PKG_TAG=""
            if [ "$BUILD_LATEST" != true ]; then
                tagCalculate $repo
                TAG=:${PKG_TAG}
            fi
            echo "Building rackhd/$repo$TAG"
            repos_tags=$repos_tags$repo$TAG" "
            cp Dockerfile ../Dockerfile.bak
            if [ "$repo" != "on-core" ];then
                    # Use the new sources.list
                    sed -i "/^FROM/a RUN mv /etc/apt/sources.list /etc/apt/sources.list.bak\nADD $SOURCE_LIST /etc/apt/sources.list" Dockerfile
                    #Based on newly build upstream image to build
                    sed -i "/^FROM/ s/$/${PRE_TAG}/" Dockerfile
                    # Recover the sources.list
                    sed -i -e "\$aRUN mv /etc/apt/sources.list.bak /etc/apt/sources.list" Dockerfile
                    docker build -t rackhd/$repo$TAG .
            fi
            case $repo in
                "on-core")
                    docker build -t rackhd/$repo$TAG .
                    PRE_TAG=$TAG
                    ;;
                "on-tasks")
                    PRE_TAG=$TAG
                    ;;
            esac 
            mv ../Dockerfile.bak Dockerfile
        popd
    done

    # write build list to a file for guiding image push. 
    pushd $WORKDIR
    echo "Imagename:tag list of this build is $repos_tags"
    echo $repos_tags >> build_record
    popd
}

# Build begins
pushd $WORKDIR

pushd RackHD
    #get rackhd changelog Version
    RACKHD_CHANGELOG_VERSION=$(dpkg-parsechangelog --show-field Version)
popd

#record all image:tag of each build
if [ -f build_record ];then
    rm build_record
    touch build_record
fi

doBuild
if [[ "$IS_OFFICIAL_RELEASE" == true ]];then
    # latest tag is for master branch build.
    BUILD_LATEST=true
    doBuild
fi
# Build ends
popd
