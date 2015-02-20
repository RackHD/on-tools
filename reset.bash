#!/bin/bash
set -x
# FOG
cd ~/src/renasar-fog-ui
rm -rf node_modules
rm -rf dist
rm -rf bower_components
npm install
npm run build
npm test
# DHCP
cd ~/src/renasar-dhcp
rm -rf node_modules
npm install
# TFTP
cd ~/src/renasar-tftp
rm -rf node_modules
npm install
# HTTP
cd ~/src/renasar-http
rm -rf node_modules
npm install
npm run apidoc
# SYSLOG
cd ~/src/renasar-syslog
rm -rf node_modules
npm install
# TASKGRAPH
cd ~/src/renasar-taskgraph
rm -rf node_modules
npm install
# reset AMQP
rabbitmqctl stop_app; rabbitmqctl force_reset; rabbitmqctl start_app
