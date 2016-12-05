## indexMigration.py

This is a tool used for dropping the indexes from current mongo databases.
Before removing the indexes, the script will first backup the mongo databases
and save it with the name "dump.bak" in the working directory.

__Note:__ Usage below:
```
python indexMigration.py
```
