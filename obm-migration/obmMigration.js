var di = require('di');
var core = require('on-core')(di);
var injector = new di.Injector(core.injectables);
var waterline = injector.get('Services.Waterline');
var waterlineProtocol = injector.get('Protocol.Waterline');
var _ = require('lodash');
var Promise = injector.get('Promise');
var exec = require('child_process').exec;
var encryption = injector.get('Services.Encryption');

// Override waterline message publish with no-op.
waterlineProtocol.publishRecord = function () {
    return Promise.resolve();
};

exec('mongodump', function(error, stdout, stderr) { // Backup mongo
 
    encryption.start()
        .then (function(){
             return waterline.start();
        })
        .then(function () {
            return waterline.obms.setIndexes();
        })
        .then(function () {
            // Get node documents.
            // Use native mongo, since new node model doesn't include old obm settings.
            return waterline.nodes.findMongo();
        })
        .then(function (nodeDocuments) {
            // Save OBM settings using OBM model.
            var obmSavesToBeDone = [];
            _.forEach(nodeDocuments, function (thisNode) {
                var nodeId = thisNode._id.toString();
                console.log(nodeId);
                var obmSettingsList = thisNode.obmSettings;
                if (obmSettingsList) {
                    _.forEach(obmSettingsList, function (obmSettings) {
                        console.log('Saving: ' + nodeId + ' ' + JSON.stringify(obmSettings));
                        var obmSave = waterline.obms.upsertByNode(nodeId, obmSettings)
                            .catch(function (err) {
                                console.log('Error saving OBM record: ' + err.message);
                            });
                        obmSavesToBeDone.push(obmSave);
                    });
                }
            });

            return Promise.all(obmSavesToBeDone);
        })
        .then(function () {
            // Delete OBM settings from all node documents.
            console.log('Removing node OBM settings...');
            
            var query = {
                obmSettings: {
                    $exists: true
                }
            };
            var update = {
                $set: {
                    updatedAt: new Date()
                },
                $unset: {
                    obmSettings: ""
                }
            };
            var options = {
                multi: true
            };

            return waterline.nodes.runNativeMongo('update', [query, update, options]);
        })
        .then(function () {
            waterline.stop();
        });
});
