#!/bin/bash

# Copyright 2015, EMC, Inc.

# set up screen ala DevStack
screen -AmdS renasar -t shell -s /bin/bash
SCREEN_HARDSTATUS='%{= .} %-Lw%{= .}%> %n%f %t*%{= .}%+Lw%< %-=%{g}(%{d}%H/%l%{g})'
sleep 1 # wait for screen to fully establish
screen -r renasar -X hardstatus alwayslastline "$SCREEN_HARDSTATUS"

# send commands to screen session to run the processes in new 'windows' with titles specific to the commands
#screen -S renasar -p shell -X screen -t top /bin/bash -c 'top'
screen -S renasar -p shell -X screen -t http /bin/bash -c 'less -R /var/log/upstart/on-http.log'
screen -S renasar -p shell -X screen -t taskgraph /bin/bash -c 'less -R /var/log/upstart/on-taskgraph.log'
screen -S renasar -p shell -X screen -t syslog /bin/bash -c 'less -R /var/log/upstart/on-syslog.log'
screen -S renasar -p shell -X screen -t dhcp /bin/bash -c 'less -R /var/log/upstart/on-dhcp.log'
screen -S renasar -p shell -X screen -t tftp /bin/bash -c 'less -R /var/log/upstart/on-tftp.log'

echo "use 'screen -R' to connect to the screens."
echo 'Control-a " to get a list and select screens'
echo 'Control-a d to detach from the screen.'
