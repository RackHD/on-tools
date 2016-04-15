## scripts

This is a location to place useful development scripts and document them here.

## setup_iso.py

This is a tool used for deploying ISO file contents to the specified
destination directory such that the destination directory can be used as a
target for RackHD OS bootstrap workflows

__Note:__ Usage below:
```
setup_iso.py [http://path.to/file.iso | /path/to/file.iso] [/var/destination]
```

Within a vanilla RackHD installation, we would commonly expect the last argument
to be one of the below options:
```
/opt/monorail/static/http/
/home/<user>/src/on-http/static/http/
```
