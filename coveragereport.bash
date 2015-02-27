#!/bin/bash

PROJECTS="renasar-core renasar-dhcp renasar-http renasar-tftp renasar-syslog renasar-tasks renasar-taskgraph"

cd ..
for PROJ in ${PROJECTS}; do echo "Coverage for ${PROJ}"
    pushd ${PROJ}
    rm -rf node_modules/
    npm install
    grunt coverage
    open coverage/index.html
    popd
done
