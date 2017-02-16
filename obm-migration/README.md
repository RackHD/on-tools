# rackhd-obm-migration
Tool for migrating RackHD OBM, ssh, and SNMP settings from the Mongo nodes collection to the obms and ibms collections, used by the 2.0 OBM and IBM model

## Installation

    clone this repository
    cd to the cloned directory
    npm install

## Running the migration script

    mongodump
    mv dump dump.save
    node obmMigration.js

NOTE: All mongo databases are backed up into the ./dump directory on startup. Use mongorestore to restore the database from backup.
