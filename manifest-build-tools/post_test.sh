#!/bin/bash

############################################
# Post-Test scripts for ova, vagrantBox and docker.
# This script will up/deploy ova, box and docker images,
# Then check if RackHD services are good running.
#
# Usage: 
# post_test.sh \
# --type ova, vagrant or docker
#
# ova-post-test need some special parameter of net config and target esxi server
# --adminIP ***.***.***.***
# --adminGateway ***.***.***.***
# --adminNetmask 255.255.255.0
# --adminDNS ***.***.***.***
# --net "ADMIN"="External Connection"
# --datastore some-datastore
# --deployName ova-for-post-test
# --ovaFile /someDir/some.ova
# --vcenterHost ***.***.***.***
# --ntName user
# --ntPass password
# --esxiHost ***.***.***.***
#
# vagrant-post-test need some special parameter of boxFile and controlNetwork name
# --boxFile ./someDir/some.box
# --controlNetwork vmnet*
# --
#
# docker-post-test need some special parameter of docker build record file and cloned RackHD repo
# --RackHDDir ./someDir/RackHD
# --buildRecord ./record_file
# A recorde_file contains repo:tag of all rackhd repos which build in one docker build, its format is like this:
# repo1:tag1 repo2:tag2 ......
# If build twice in one docker build job, the repos:tags of each build will be stored in each line
############################################

set -x

while [ "$1" != "" ];do
    case $1 in
        --type)
            shift
            type=$1;;
        --adminIP)
            shift
            adminIP=$1;;
        --adminGateway)
            shift
            adminGateway=$1;;
        --adminNetmask)
            shift
            adminNetmask=$1;;
        --adminDNS)
            shift
            adminDNS=$1;;
        --net)
            shift
            net=$1;;
        --datastore)
            shift
            datastore=$1;;
        --deployName)
            shift
            deployName=$1;;
        --ovaFile)
            shift
            ovaFile=$1;;
        --vcenterHost)
            shift
            vcenterHost=$1;;
        --ntName)
            shift
            ntName=$1;;
        --ntPass)
            shift
            ntPass=$1;;
        --esxiHost)
            shift
            esxiHost=$1;;
        --boxFile)
            shift
            boxFile=$1;;
        --controlNetwork)
            shift
            controlNetwork=$1;;
        --RackHDDir)
            shift
            RackHDDir=$1;;
        --buildRecord)
            shift
            buildRecord=$1;;
        *)
        exit 1
    esac
    shift
done

findRackHDService() {
    case $type in
        ova)
        # ova northPort default to 8080
        api_test_result=`ansible ova-for-post-test -a "wget --retry-connrefused --waitretry=1 --read-timeout=20 --timeout=15 -t 1 --continue localhost:8080/api/2.0/nodes"`
        echo $api_test_result | grep "$service_normal_sentence" > /dev/null  2>&1
        ;;
        docker)
        # docker southPort default to 9080
        wget --retry-connrefused --waitretry=1 --read-timeout=20 --timeout=15 -t 1 --continue http://172.31.128.1:9080/api/2.0/nodes
        ;;
        vagrant)
        # Vagrantfile northPort default to 9090
        curl 127.0.0.1:9090/api/2.0/nodes
        ;;
    esac
}

waitForAPI() {
    #will be edit after build own ova
    service_normal_sentence="Authentication Failed"
    timeout=0
    maxto=60
    while [ ${timeout} != ${maxto} ]; do
        findRackHDService
        if [ $? = 0 ]; then
          echo "RackHD services perform normally!"
          break
        fi
        sleep 10
        timeout=`expr ${timeout} + 1`
    done
    if [ ${timeout} == ${maxto} ]; then
        echo "Timed out waiting for RackHD API service (duration=`expr $maxto \* 10`s)."
        exit 1
      fi
}

############################################
# ova post test
############################################

deploy_ova() {
    echo yes | ovftool \
    --prop:adminIP=$adminIP  --prop:adminGateway=$adminGateway --prop:adminNetmask=$adminNetmask  --prop:adminDNS=$adminDNS \
    --overwrite --powerOffTarget --powerOn --skipManifestCheck \
    --net:$net \
    --datastore=$datastore \
    --name=$deployName \
    ${ovaFile} \
    vi://${ntName}:${ntPass}@${vcenterHost}/Infrastructure@onrack.cn/host/${esxiHost}/
    ssh-keygen -f "$HOME/.ssh/known_hosts" -R $adminIP
}

delete_ova() {
	ansible esxi -a "./vm_operation.sh -a delete ${esxiHost} 1 $deployName"
    if [ $? = 0 ]; then
      echo "Delete $deployName successfully!"
    fi
}

post_test_ova() {
    delete_ova
    deploy_ova
    waitForAPI
    delete_ova
}

############################################
# vagrant post test
############################################

create_vagrant_file() {
    wget vagrantFile -O Vagrantfile.in
    sed -e "s#rackhd/rackhd#${boxFile}#g" \
        -e '/target.vm.box_version/d' \
        -e "s#em1#${controlNetwork}#g" \
        Vagrantfile.in > Vagrantfile
}

post_test_vagrant() {
    vagrant destroy -f
    vagrant up --provision
    waitForAPI
    vagrant destroy -f
}

############################################
# docker post test
############################################

clean_all_containers() {
    docker stop $(docker ps -a -q)
    docker rm $(docker ps -a -q)
}

post_test_docker() {
    clean_all_containers
    cd $RackHDDir/docker 
    #if clone file name is not repo name, this scirpt should be edited.
    while read -r LINE; do
        cp docker-compose-mini.yml docker-compose-mini.yml.bak
        for repo_tag in $LINE; do
            repo=${repo_tag%:*}
            sed -i "s#rackhd/${repo}.*#rackhdmirror/${repo_tag}#g" docker-compose-mini.yml
        done
        docker-compose -f docker-compose-mini.yml pull --ignore-pull-failures
        docker-compose -f docker-compose-mini.yml up -d
        mv docker-compose-mini.yml.bak docker-compose-mini.yml
        waitForAPI
        clean_all_containers
    done < $buildRecord
}

############################################
# run post test
############################################
case $type in
    ova)
    post_test_ova
    ;;
    docker)
    post_test_docker
    ;;
    vagrant)
    post_test_vagrant 
    ;;
esac
