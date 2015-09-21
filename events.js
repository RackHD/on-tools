// Copyright 2015, EMC, Inc.
/* jshint: node:true */

'use strict';

var di = require('di'),
    core = require('on-core')(di),
    injector = new di.Injector(
        core.injectables
    ),
    logger = injector.get('Logger').initialize('Events Sink'),
    messenger = injector.get('Services.Messenger');

messenger.start().then(function () {
    return messenger.subscribe('on.events', '#', function (e) {
        console.log(e);
    });
}).catch(function (error) {
    logger.error(error, { error: error });
});

process.on('SIGINT', function () {
   messenger.stop();
});

