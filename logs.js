// Copyright 2015, EMC, Inc.
/* jshint: node:true */

'use strict';

var di = require('di'),
    core = require('on-core')(di),
    injector = new di.Injector(
        core.injectables
    ),
    logger = injector.get('Logger').initialize('Logs Sink'),
    messenger = injector.get('Services.Messenger');

messenger.start().then(function () {
    return messenger.subscribe('on.logging', '#', function (e) {
        e.print();
    });
}).catch(function (error) {
    logger.error(error.message, { error: error });
});

process.on('SIGINT', function () {
    messenger.stop();
});

