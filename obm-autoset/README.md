# RackHD IPMI OBM Setting Auto Set Tool
Tool to apply OBM setting for each compute node discovered by RackHD. Save the trouble to manually apply OBM setting node by node.

## Usage
Downlaod this folder.
Make sure you have python 2 or python 3 installed
cd to the cloned directory.
Change the environment setting in obm_setting.json file.
python ApplyOBMSetting.py -ora 192.168.129.96

## Theory of Operation
The script will check the RMM/BMC address information in the catalog of ora. And then put OBM setting to ora by RackHD 2.0 API. The compute node should be discovered by RackHD ora first.

## Supported parameters
### -ora
Specify RackHD ora IP address, default use localhost

### -user
Override the usernames in OBM setting file, default is "None"

### -password
Override the password in OBM setting file, default is "None"



### -v {0,2,4,6,9}
Verbosity level of console output:
0: No debug,
2: User script output
4: rest calls and status info
6: other common calls (ipmi, ssh)
9: all the rest
defualt is 0

### -nodeid {NODEID}
Specify one compute node to apply OBM setting instead of apply OBM setting to all Nodes. default:all")

### -auth {on/off}
Specify if authentication is on/off , default:off


## obm_setting.json Config File
This file contains the credentials required to access the ora/bmcs. It includes:
"ora": RackHD ora ssh credential.
"bmc": bmc/rmm credential list.
"api": RackHD api login credential
"ports":http/https tcp port number.
