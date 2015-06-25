// Copyright (c) 2015, EMC Corporation

'use strict';

var di = require('di'),
    core = require('on-core')(di),
    injector = new di.Injector(
        core.injectables
    ),
    messenger = injector.get('Services.Messenger'),
    assert = injector.get('Assert');

var args = process.argv.slice(2);

try {
    assert.string(args[0], "AMQP Exchange");
    assert.string(args[1], "AMQP RoutingKey");
} catch (e) {
    console.log(e);
    process.exit(1);
}

messenger.start().then(function () {
    messenger.subscribe(args[0], args[1], function (event, data) {
        console.log(data.deliveryInfo.routingKey);
        console.log(event);
    }).done();
}).catch(function (error) {
    console.log(error);
});

process.on('SIGINT', function () {
    messenger.stop();
});
