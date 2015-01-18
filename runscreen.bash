#!/bin/bash

# set up screen ala DevStack
screen -AmdS renasar -t shell -s /bin/bash
SCREEN_HARDSTATUS='%{= .} %-Lw%{= .}%> %n%f %t*%{= .}%+Lw%< %-=%{g}(%{d}%H/%l%{g})'
screen -r renasar -X hardstatus alwayslastline "$SCREEN_HARDSTATUS"

# send commands to screen session to run the processes in new 'windows' with titles specific to the commands
screen -S renasar -p shell -X screen -t top /bin/bash -c 'top'
screen -S renasar -p shell -X screen -t rabbit /bin/bash -c 'rabbitmq-server'
sleep 5 # wait for rabbitMQ to be running
screen -S renasar -p shell -X screen -t taskgraph /bin/bash -c 'cd ~/src/renasar-taskgraph; sudo node index.js'
screen -S renasar -p shell -X screen -t dhcp /bin/bash -c 'cd ~/src/renasar-dhcp; sudo node index.js'
screen -S renasar -X screen -t tftp /bin/bash -c 'cd ~/src/renasar-tftp; sudo node index.js'
screen -S renasar -X screen -t syslog /bin/bash -c 'cd ~/src/renasar-syslog; sudo node index.js'
screen -S renasar -p shell -X screen -t http /bin/bash -c 'cd ~/src/renasar-http; sudo node index.js'

echo "use 'screen -R' to connect to the screens."
echo 'Control-a " to get a list and select screens'
echo 'Control-a d to detach from the screen.'
