## RackHD BIST 

RackHD Built In Self Test can be used to check health status of RackHD environment and configuration.

## rackhd_bist.py

This script will run RackHD BIST and log necessary information.

Follow the below instructions to use this tool:

 1. Configure following items in bist_user_config.json file:

    + **sourceCodeRepo**: folder path that stores RackHD source code, if not configured it is "/var/renasar/"
    + **logPath**: RackHD BIST log path, BIST logs will be stored in the path, if not configured it is "/var/log/rackhd/"
    + **apis**: RackHD APIs user wants to test, if not configured only SKU api will be tested
    + **optionalStaticFiles**: static files user wants to check existence, if not configured only necessary static files will be checked

 2. Install Dependencies
    ```
    /on-tools/rackhd_bist$ pip install pika
    ```

 3. Run script 
    ```
    /on-tools/dev_tools$ sudo python rackhd_bist.py --path <rackhd_source_code_repo> --start
    ```

    + **--path**: Specify RackHD source code repository path. If not specified, script will load source code repository path from bist_user_config.json
    + **--start**: Leave RackHD services started after test, if rackhd_bist.py is run without this argument, RackHD services will be stopped after test


