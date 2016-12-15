## dev_tools

This is a location to place useful development nodejs code and document them here.

## sniff.js

This process will allow the user to monitor our messaging queue and could be extended
to be an event based handler. This code is expected to be run from a running monorail server.

Follow the below instructions to begin using this tool,

1.Install Dependencies.
```
/on-tools/dev_tools$ npm install
```

2.Run Process (collecting all messages from the events exchange).
```
/on-tools/dev_tools$ sudo node sniff.js "on.events" "#"
```

__Note:__ The above command usage is below:
```
sniff.js <AMQP_Exchange> <AMQP_RoutingKey>
```

Visit our documentation [here](http://rackhd.readthedocs.org/en/latest/devguide/index.html) to find available Exchanges and Routing Keys.
