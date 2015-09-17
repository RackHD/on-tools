#!/bin/bash

# Copyright 2015, EMC, Inc.

set -x
# FOG
cd ~/src/on-fog-ui
rm -rf node_modules
rm -rf dist
rm -rf bower_components
npm install
npm run build
npm test
# DHCP
cd ~/src/on-dhcp
rm -rf node_modules
npm install
# TFTP
cd ~/src/on-tftp
rm -rf node_modules
npm install
# HTTP
cd ~/src/on-http
rm -rf node_modules
npm install
npm run apidoc
# SYSLOG
cd ~/src/on-syslog
rm -rf node_modules
npm install
# TASKGRAPH
cd ~/src/on-taskgraph
rm -rf node_modules
npm install
# reset AMQP
rabbitmqctl stop_app; rabbitmqctl force_reset; rabbitmqctl start_app
