// Copyright 2014, Renasar Technologies Inc.
/* jshint: node:true */

'use strict';

var di = require('di'),
    core = require('renasar-core')(di),
    injector = new di.Injector(
        core.injectables
    ),
    logger = injector.get('Logger').initialize('Logs Sink'),
    messenger = injector.get('Services.Messenger');

messenger.start().then(function () {
    messenger.exchange('logging', 'topic', {
        durable: true
    }).then(function () {
        messenger.subscribe('logging', '#', function (logEvent) {
            logEvent.print();
        }).done();
    });
}).catch(function (error) {
    logger.error(error, { error: error });
});

process.on('SIGINT', function () {
    messenger.stop();
});
