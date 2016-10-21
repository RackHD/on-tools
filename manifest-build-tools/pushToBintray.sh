#!/bin/bash

#Sample Usage: pushToBintray.sh username api_key bintray_repo bintray_package_name bintray_package_version local_package_path

set -e

BINTRAY_CONFIG_FILE=bintray.conf
if [ ! -f "$BINTRAY_CONFIG_FILE" ]; then
    echo "The bintray.conf is missing, exiting now..."
    exit 1
fi

source $BINTRAY_CONFIG_FILE
BINTRAY_USER=$1
BINTRAY_API_KEY=$2
BINTRAY_REPO=$3
BINTRAY_PCK=$4
BINTRAY_PCK_VERSION=$5
PACKAGE_PATH=$6

main() {
  CURL="curl -u${BINTRAY_USER}:${BINTRAY_API_KEY} -H Content-Type:application/json -H Accept:application/json"
  if (check_package_exists); then
    echo "The package ${BINTRAY_PCK} does not exist. Exiting now..."
    exit 1
  fi

  if (check_version_exists); then
    echo "The version ${BINTRAY_PCK_VERSION} does not exist. Exiting now..."
    exit 1
  fi
  deploy_package
}

check_package_exists() {
  echo "Checking if package ${BINTRAY_PCK} exists..."

  if [ $(${CURL} --write-out %{http_code} --silent --output /dev/null -X GET ${API}/packages/${BINTRAY_USER}/${BINTRAY_REPO}/${BINTRAY_PCK}) -eq "200" ]; then
      echo "package already exists"
      return 1
  else
      return 0
  fi
}

check_version_exists() {
  echo "Checking if version ${BINTRAY_PCK_VERSION} exists..."
  if [ $(${CURL} --write-out %{http_code} --silent --output /dev/null -X GET ${API}/packages/${BINTRAY_USER}/${BINTRAY_REPO}/${BINTRAY_PCK}/versions/${BINTRAY_PCK_VERSION}) -eq "200" ]; then
      echo "version already exists"
      return 1
  else
      return 0
  fi
}

deploy_package() {
  if (upload_content); then
    echo "Publishing ${PACKAGE_PATH}..."
    if [ $(${CURL} --write-out %{http_code} --silent --output /dev/null -X POST ${API}/content/${BINTRAY_USER}/${BINTRAY_REPO}/${BINTRAY_PCK}/${BINTRAY_PCK_VERSION}/publish) -eq "200" ]; then
      echo "Package ${PACKAGE_PATH} published"
    else
      echo "Failed to publish your package ${PACKAGE_PATH}"
    fi
  fi
}

upload_content() {
  echo "Uploading ${PACKAGE_PATH}..."
  if [ $(${CURL} --write-out %{http_code} --silent --output /dev/null -H X-Bintray-Debian-Distribution:${DISTRIBUTION} -H X-Bintray-Debian-Component:${COMPONENT} -H X-Bintray-Debian-Architecture:${ARCHITECTURE} -H X-Bintray-Override:1 -T ${PACKAGE_PATH} ${API}/content/${BINTRAY_USER}/${BINTRAY_REPO}/${BINTRAY_PCK}/${BINTRAY_PCK_VERSION}/ ) -eq "201" ]; then
      echo "Package ${PACKAGE_PATH} uploaded"
      return 0
  else
      echo "Failed to upload package ${PACKAGE_PATH}"
      return 1
  fi
}

main "$@"
