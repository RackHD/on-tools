#!/bin/bash

############################################
# Usage: 
# pushToBintray.sh \
# --user username \
# --api_key api_key \
# --subject subject \
# --repo bintray_repo \
# --package bintray_package_name \
# --version bintray_package_version \
# --file_path local_package_path \
# --component "main" \
# --distribution "trusty" \
# --architecture "amd64,i386"
#
# The parameters are required:
# user, api_key, subject, repo, package, version, file_path,
# Below parameters are optional:
# component (default: main)
# distribution (default: trusty)
# architecture (default: amd64)
############################################

set -e
set -x

while [ "$1" != "" ];do
    case $1 in
        --user)
            shift
            BINTRAY_USER=$1;;
        --api_key)
            shift
            BINTRAY_API_KEY=$1;;
        --subject)
            shift
            BINTRAY_SUBJECT=$1;;
        --repo)
            shift
            BINTRAY_REPO=$1;;
        --package)
            shift
            BINTRAY_PCK=$1;;
        --version)
            shift
            BINTRAY_PCK_VERSION=$1;;
        --file_path)
            shift
            PACKAGE_PATH=$1;;
        --component)
            shift
            COMPONENT=$1;;
        --distribution)
            shift
            DISTRIBUTION=$1;;
        --architecture)
            shift
            ARCHITECTURE=$1;;
        *)
        exit 1
    esac
    shift
done
BINTRAY_API="https://api.bintray.com"
if [ -z "$BINTRAY_USER" ]
then
   echo "Must specify \$user of bintray"
   exit 1
fi

if [ -z "$BINTRAY_API_KEY" ]
then
   echo "Must specify \$api_key of bintray"
   exit 1
fi

if [ -z "$BINTRAY_SUBJECT" ]
then
   echo "Must specify \$subject of bintray"
   exit 1
fi

if [ -z "$BINTRAY_REPO" ]
then
   echo "Must specify \$repo of bintray"
   exit 1
fi

if [ -z "$BINTRAY_PCK" ]
then
   echo "Must specify \$package of bintray"
   exit 1
fi

if [ -z "$BINTRAY_PCK_VERSION" ]
then
   echo "Must specify \$version of bintray"
   exit 1
fi

if [ -z "$PACKAGE_PATH" ]
then
   echo "Must specify \$file_path which is going to be uploaded to bintray"
   exit 1
fi

if [ -z "$COMPONENT" ]
then
    COMPONENT="main"
fi

if [ -z "$DISTRIBUTION" ]
then
    DISTRIBUTION="trusty"
fi

if [ -z "$ARCHITECTURE" ]
then
    ARCHITECTURE="amd64"
fi

main() {
  CURL="curl -u${BINTRAY_USER}:${BINTRAY_API_KEY} -H Content-Type:application/json -H Accept:application/json"
  if (check_package_exists); then
    echo "The package ${BINTRAY_PCK} does not exist. Creating now..."
    create_package
  fi

  if (check_version_exists); then
    echo "The version ${BINTRAY_PCK_VERSION} does not exist. Creating now..."
    create_version
  fi
  deploy_package
}

check_package_exists() {
  echo "Checking if package ${BINTRAY_PCK} exists..."

  if [ $(${CURL} --write-out %{http_code} --silent --output /dev/null -X GET ${BINTRAY_API}/packages/${BINTRAY_SUBJECT}/${BINTRAY_REPO}/${BINTRAY_PCK}) -eq "200" ]; then
      echo "package already exists"
      return 1
  else
      return 0
  fi
}

check_version_exists() {
  echo "Checking if version ${BINTRAY_PCK_VERSION} exists..."
  if [ $(${CURL} --write-out %{http_code} --silent --output /dev/null -X GET ${BINTRAY_API}/packages/${BINTRAY_SUBJECT}/${BINTRAY_REPO}/${BINTRAY_PCK}/versions/${BINTRAY_PCK_VERSION}) -eq "200" ]; then
      echo "version already exists"
      return 1
  else
      return 0
  fi
}

create_package() {
  echo "Creating package ${BINTRAY_PCK}..."
  data="{
  \"name\": \"${BINTRAY_PCK}\",
  \"desc\": \"This package ...\",
  \"vcs_url\": \"auto\",
  \"licenses\": [\"Apache-2.0\"]
  }"

  if [ $(${CURL} --write-out %{http_code} --silent --output /dev/null -X POST ${BINTRAY_API}/packages/${BINTRAY_SUBJECT}/${BINTRAY_REPO} --data "${data}") -eq "201" ];then
    echo "Succeed to create package ${BINTRAY_PCK}."
  else
    echo "Failed to create package ${BINTRAY_PCK}."
    exit 1
  fi
}

create_version() {
  echo "Creating version ${BINTRAY_PCK_VERSION}..."
  data="{
  \"name\": \"${BINTRAY_PCK_VERSION}\",
  \"desc\": \"This version ...\"
  }"

  if [ $(${CURL} --write-out %{http_code} --silent --output /dev/null -X POST ${BINTRAY_API}/packages/${BINTRAY_SUBJECT}/${BINTRAY_REPO}/${BINTRAY_PCK}/versions --data "${data}") -eq "201" ];then
    echo "Succeed to create version ${BINTRAY_PCK_VERSION}."
  else
    echo "Failed to create version ${BINTRAY_PCK_VERSION}."
    exit 1
  fi
}

deploy_package() {
  if (upload_content); then
    echo "Publishing ${PACKAGE_PATH}..."
    if [ $(${CURL} --write-out %{http_code} --silent --output /dev/null -X POST ${BINTRAY_API}/content/${BINTRAY_SUBJECT}/${BINTRAY_REPO}/${BINTRAY_PCK}/${BINTRAY_PCK_VERSION}/publish) -eq "200" ]; then
      echo "Package ${PACKAGE_PATH} published"
    else
      echo "Failed to publish your package ${PACKAGE_PATH}"
    fi
  fi
}

upload_content() {
  echo "Uploading ${PACKAGE_PATH}..."

  if [ $(${CURL} --write-out %{http_code} --silent --output /dev/null -H X-Bintray-Debian-Distribution:${DISTRIBUTION} -H X-Bintray-Debian-Component:${COMPONENT} -H X-Bintray-Debian-Architecture:${ARCHITECTURE} -H X-Bintray-Override:1 -T ${PACKAGE_PATH} ${BINTRAY_API}/content/${BINTRAY_SUBJECT}/${BINTRAY_REPO}/${BINTRAY_PCK}/${BINTRAY_PCK_VERSION}/ ) -eq "201" ]; then
      echo "Package ${PACKAGE_PATH} uploaded"
      return 0
  else
      echo "Failed to upload package ${PACKAGE_PATH}"
      return 1
  fi
}

main "$@"
