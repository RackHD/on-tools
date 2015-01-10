// Copyright 2014, Renasar Technologies Inc.
/* jshint: node:true */

'use strict';

var di = require('di'),
    core = require('renasar-core')(di),
    injector = new di.Injector(
        core.injectables
    ),
    logger = injector.get('Logger').initialize('Events Sink'),
    messenger = injector.get('Services.Messenger');

messenger.start().then(function () {
    messenger.exchange('events', 'topic', {
        durable: true
    }).then(function () {
        messenger.subscribe('events', '#', function (message) {
            console.log(message.data);
        }).done();
    });
}).catch(function (error) {
    logger.error(error, { error: error });
});

process.on('SIGINT', function () {
    messenger.stop();
});