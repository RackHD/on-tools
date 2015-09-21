#!/bin/bash

# Copyright 2015, EMC, Inc.

PROJECTS="on-core on-dhcp on-http on-tftp on-syslog on-tasks on-taskgraph"

cd ..
for PROJ in ${PROJECTS}; do echo "Coverage for ${PROJ}"
    pushd ${PROJ}
    rm -rf node_modules/
    npm install
    grunt coverage
    open coverage/index.html
    popd
done
