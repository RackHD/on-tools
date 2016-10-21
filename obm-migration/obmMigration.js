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
            return Promise.all([waterline.obms.setIndexes(), waterline.ibms.setIndexes()]);
        })
        .then(function () {
            // Get node documents.
            // Use native mongo, since new node model doesn't include old obm settings.
            return waterline.nodes.findMongo();
        })
        .then(function (nodeDocuments) {
            // Save OBM and SSH settings using OBM and IBM models.
            var settingsSavesToBeDone = [];
            _.forEach(nodeDocuments, function (thisNode) {
                var nodeId = thisNode._id.toString();
                console.log(nodeId);
                var obmSettingsList = thisNode.obmSettings;
                var sshSettings = thisNode.sshSettings;
                if (obmSettingsList) {
                    _.forEach(obmSettingsList, function (obmSettings) {
                        console.log('Saving: ' + nodeId + ' ' + JSON.stringify(obmSettings));
                        var obmSave = waterline.obms.upsertByNode(nodeId, obmSettings)
                            .catch(function (err) {
                                console.log('Error saving OBM record: ' + err.message);
                            });
                        settingsSavesToBeDone.push(obmSave);
                    });
                }
                if (sshSettings) {
                    console.log('Saving: ' + nodeId + ' ' + JSON.stringify(sshSettings));
                    var newSshSettings = {};
                    newSshSettings.config = sshSettings;
                    newSshSettings.service = 'ssh-ibm-service';
                    var ibmSave = waterline.ibms.upsertByNode(nodeId, newSshSettings)
                        .catch(function (err) {
                            console.log('Error saving IBM record: ' + err.message);
                        });
                    settingsSavesToBeDone.push(ibmSave);
                }
            });

            return Promise.all(settingsSavesToBeDone);
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

            return waterline.nodes.runNativeMongo(
                'update', [query, update, options]
            );
        })
        .then(function () {
            // Delete SSH settings from all node documents.
            console.log('Removing node SSH settings...');

            var query = {
                sshSettings: {
                    $exists: true
                }
            };
            var update = {
                $set: {
                    updatedAt: new Date()
                },
                $unset: {
                    sshSettings: ""
                }
            };
            var options = {
                multi: true
            };
            return waterline.nodes.runNativeMongo(
                'update', [query, update, options]
            );
        })
        .then(function () {
            waterline.stop();
        });
});
