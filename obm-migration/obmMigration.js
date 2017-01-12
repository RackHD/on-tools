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

function _deleteSettings(settings) {
    var query = {};
    query[settings] = {$exists: true};
    var update = {
        $set: {
            updatedAt: new Date()
        }
    };
    update.$unset = {};
    update.$unset[settings] = "";
    var options = {
        multi: true
    };

    return waterline.nodes.runNativeMongo(
        'update', [query, update, options]
    );
}

function _saveObmSettings(nodeId, obmSettings) {
    return waterline.obms.upsertByNode(nodeId, obmSettings)
        .catch(function (err) {
            console.log('Error saving OBM record: ' + err.message);
        });
}

function _saveIbmSettings(nodeId, service, settings) {
    var newSettings = {};
    newSettings.config = settings;
    newSettings.service = service;

    return waterline.ibms.upsertByNode(nodeId, newSettings)
        .catch(function (err) {
            console.log('Error saving IBM record: ' + err.message);
        });
}

exec('mongodump', function(error, stdout, stderr) { // Backup mongo
 
    encryption.start()
        .then (function(){
             return waterline.start();
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
                var snmpSettings = thisNode.snmpSettings;

                if (obmSettingsList) {
                    _.forEach(obmSettingsList, function (obmSettings) {
                        console.log('Saving OBM: ' + nodeId + ' ' + JSON.stringify(obmSettings));
                        settingsSavesToBeDone.push(_saveObmSettings(nodeId, obmSettings));
                    });
                }
                if (sshSettings) {
                    console.log('Saving SSH: ' + nodeId + ' ' + JSON.stringify(sshSettings));
                    settingsSavesToBeDone.push(_saveIbmSettings(nodeId, 'ssh-ibm-service', sshSettings));
                }
                if (snmpSettings) {
                    console.log('Saving SNMP: ' + nodeId + ' ' + JSON.stringify(snmpSettings));
                    settingsSavesToBeDone.push(_saveIbmSettings(nodeId, 'snmp-ibm-service', snmpSettings));
                }
            });

            return Promise.all(settingsSavesToBeDone);
        })
        .then(function () {
            console.log('Removing node OBM settings...');
            return _deleteSettings('obmSettings');
        })
        .then(function () {
            console.log('Removing node SSH settings...');
            return _deleteSettings('sshSettings');
        })
        .then(function () {
            console.log('Removing node SNMP settings...');
            return _deleteSettings('snmpSettings');
        })
        .then(function () {
            waterline.stop();
        });
});
