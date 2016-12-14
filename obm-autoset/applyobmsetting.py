'''Copyright 2016, DELL|EMC, Inc.

Author(s):
Norton Luo


RackHD OBM setting automatic set utility
'''


import os
import sys

# External imports
try:
    import requests
except IOError:
    print "Python 'requests' package required for this script." \
          "\nUse: 'pip install requests'\nExiting...\n"
    exit(1)
try:
    import pexpect
except IOError:
    print "Python 'pexpect' package required for this script." \
          "\nUse: 'pip install pexpect'\nExiting...\n"
    exit(1)

# Check if CI_TOOLS_PATH environment variable is set.  If not, take a stab that the
# test-tools stash repository is located at same level as tests repository in the user environment
# _no_tools_repository = False
# _path_add = os.environ.get('CI_TOOLS_PATH',"../../test-tools")
# sys.path.append(_path_add)
# try:
#     import reporter
#     import reporter.utils
# except ImportError:
#     _no_tools_repository = True


# Standard imports
import json
import argparse
import subprocess
import time, datetime
import sys
import unittest
import signal
import argparse
#Load OBM config file
try:
    OBM_CONFIG = json.loads(open("obm_config.json").read())
except:
    print "**** Global Config file: " + "global_config.json" + " missing or corrupted! Exiting...."
    sys.exit(255)


def get_auth_token():
    # This is run once to get an auth token which is set to global AUTH_TOKEN and used for rest of session
    global AUTH_TOKEN
    global REDFISH_TOKEN
    api_login = {"username": OBM_CONFIG["api"]["admin_user"], "password": OBM_CONFIG["api"]["admin_pass"]}
    redfish_login = {"UserName": OBM_CONFIG["api"]["admin_user"], "Password": OBM_CONFIG["api"]["admin_pass"]}
    try:
        restful("https://" + arg_ora  + ":" + str(API_PORT) +
                       "/login", rest_action="post", rest_payload=api_login, rest_timeout=2)
    except:
        AUTH_TOKEN = "Unavailable"
        return False
    else:
        api_data = restful("https://" + arg_ora + ":" + str(API_PORT) +
                           "/login", rest_action="post", rest_payload=api_login, rest_timeout=2)
        if api_data['status'] == 200:
            AUTH_TOKEN = str(api_data['json']['token'])
            redfish_data = restful("https://" + arg_ora + ":" + str(API_PORT) +
                               "/redfish/v1/SessionService/Sessions", rest_action="post", rest_payload=redfish_login, rest_timeout=2)
            if 'x-auth-token' in redfish_data['headers']:
                REDFISH_TOKEN =  redfish_data['headers']['x-auth-token']
                return True
            else:
                print "WARNING: Redfish API token not available."
        else:
            AUTH_TOKEN = "Unavailable"
            return False

def rackhdapi(url_cmd, action='get', payload={}, timeout=None, headers={}):
    '''
    This routine will build URL for RackHD API, enable port, execute, and return data
    This function is port form FIT Test, courtesy of George Paulos.
    '''

    global API_PROTOCOL
    global API_PORT

    if API_PROTOCOL == "http":
        if restful("http://" + arg_ora  + ":" + str(API_PORT) + "/", rest_timeout=2)['status'] == 0:
            print "Could not use http to connect ora, now try https..."
            API_PROTOCOL = 'https'
            API_PORT = str(OBM_CONFIG['ports']['https'])
        else:
            API_PROTOCOL = 'http'
            API_PORT = str(OBM_CONFIG['ports']['http'])

    # Retrieve authentication token for the session
    if AUTH_TOKEN == "None":
        get_auth_token()
    return restful(API_PROTOCOL + "://" + arg_ora + ":" + str(API_PORT) + url_cmd,
                       rest_action=action, rest_payload=payload, rest_timeout=timeout, rest_headers=headers)

def restful(url_command, rest_action='get', rest_payload={}, rest_timeout=None, sslverify=False, rest_headers={}):
    '''
    This routine executes a rest API call to the host.
    This function is port form FIT Test, courtesy of George Paulos.
    '''
    result_data = None

    # print URL and action
    if VERBOSITY >= 4:
        print "restful: Action = ", rest_action, ", URL = ", url_command

    # prepare payload for XML output
    payload_print = []
    try:
        json.dumps(rest_payload)
    except:
        payload_print = []
    else:
        payload_print = json.dumps(rest_payload, sort_keys=True, indent=4,)
        if len(payload_print) > 4096:
            payload_print = payload_print[0:4096] + '\n...truncated...\n'
        if VERBOSITY >= 7 and rest_payload != []:
            print "restful: Payload =\n", payload_print

    rest_headers.update({"Content-Type": "application/json"})
    if VERBOSITY >= 5:
         print "restful: Request Headers =", rest_headers, "\n"

    # If AUTH_TOKEN is set, add to header
    if AUTH_TOKEN != "None" and AUTH_TOKEN != "Unavailable" and "authorization" not in rest_headers:
        rest_headers.update({"authorization": "JWT " + AUTH_TOKEN, "X-Auth-Token": REDFISH_TOKEN})
    # Perform rest request
    try:
        if rest_action == "get":
            result_data = requests.get(url_command,
                                       timeout=rest_timeout,
                                       verify=sslverify,
                                       headers=rest_headers)
        if rest_action == "delete":
            result_data = requests.delete(url_command,
                                          data=json.dumps(rest_payload),
                                          timeout=rest_timeout,
                                          verify=sslverify,
                                          headers=rest_headers)
        if rest_action == "put":
            result_data = requests.put(url_command,
                                       data=json.dumps(rest_payload),
                                       headers=rest_headers,
                                       timeout=rest_timeout,
                                       verify=sslverify,
                                       )

        if rest_action == "post":
            result_data = requests.post(url_command,
                                        data=json.dumps(rest_payload),
                                        headers=rest_headers,
                                        timeout=rest_timeout,
                                        verify=sslverify
                                        )

        if rest_action == "patch":
            result_data = requests.patch(url_command,
                                         data=json.dumps(rest_payload),
                                         headers=rest_headers,
                                         timeout=rest_timeout,
                                         verify=sslverify
                                         )
    except requests.exceptions.Timeout:
        return {'json':'', 'text':'',
                'status':0,
                'headers':'',
                'timeout':True}

    try:
        result_data.json()
    except ValueError:

        if VERBOSITY >= 9:
            print "restful: TEXT =\n"
            print result_data.text
        if VERBOSITY >= 6:
            print "restful: Response Headers =", result_data.headers, "\n"
        if VERBOSITY >= 4:
            print "restful: Status code =", result_data.status_code, "\n"
        return {'json':{}, 'text':result_data.text, 'status':result_data.status_code,
                'headers':result_data.headers,
                'timeout':False}
    else:

        if VERBOSITY >= 9:
            print "restful: JSON = \n"
            print json.dumps(result_data.json(), sort_keys=True, indent=4)
        if VERBOSITY >= 6:
            print "restful: Response Headers =", result_data.headers, "\n"
        if VERBOSITY >= 4:
            print "restful: Status code =", result_data.status_code, "\n"
        return {'json':result_data.json(), 'text':result_data.text,
                'status':result_data.status_code,
                'headers':result_data.headers,
                'timeout':False}

def remote_shell(shell_cmd, timeout=300, user=OBM_CONFIG['ora']['username'] , password=OBM_CONFIG['ora']['password']):
    '''
    This function is used to run ipmitool on ova
    This function is port form FIT Test, courtesy of George Paulos.
    '''
    logfile_redirect = None
    address = arg_ora
    if VERBOSITY >= 4:
        print "remote_shell: Host =", address
        print "remote_shell: Command =", shell_cmd

    if VERBOSITY >= 9:
        print "remote_shell: STDOUT =\n"
        logfile_redirect = sys.stdout

    # if localhost just run the command local
    if address == 'localhost':
        (command_output, exitstatus) = \
            pexpect.run("sudo bash -c \"" + shell_cmd + "\"",
                        withexitstatus=1,
                        events={"assword": password + "\n"},
                        timeout=timeout, logfile=logfile_redirect)
        return {'stdout':command_output, 'exitcode':exitstatus}

    # this clears the ssh key from ~/.ssh/known_hosts
    subprocess.call(["touch ~/.ssh/known_hosts;ssh-keygen -R "
                     + address  + " -f ~/.ssh/known_hosts >/dev/null 2>&1"], shell=True)

    (command_output, exitstatus) = \
            pexpect.run("ssh -q -o StrictHostKeyChecking=no -t " + user + "@"
                        + address + " sudo bash -c \\\"" + shell_cmd + "\\\"",
                        withexitstatus=1,
                        events={"assword": password + "\n"},
                        timeout=timeout, logfile=logfile_redirect)
    if VERBOSITY >= 4:
        print shell_cmd, "\nremote_shell: Exit Code =", exitstatus

    return {'stdout':command_output, 'exitcode':exitstatus}




def apply_obmsetting(nodeid):
    usr=''
    pwd=''
    response= rackhdapi('/api/2.0/nodes/'+nodeid+'/catalogs/bmc')
    bmcip= response['json']['data']['IP Address']
    if bmcip=="0.0.0.0":
        response= rackhdapi('/api/2.0/nodes/'+nodeid+'/catalogs/rmm')
        bmcip= response['json']['data']['IP Address']
    #Try credential record in config file
    if arg_username=="None":
        for creds in OBM_CONFIG['bmc']:
            if remote_shell('ipmitool -I lanplus -H ' + bmcip+' -U ' + creds['username']+' -P '+ creds['password'] + ' fru')['exitcode'] == 0:
                usr = creds['username']
                pwd = creds['password']
                break
    else:
        usr=arg_username
        pwd=arg_password
    # Put the credential to OBM settings
    if  usr!="":
        payload = { "service": "ipmi-obm-service","config": {"host": bmcip, "user": usr,"password": pwd},"nodeId": nodeid}
        api_data = rackhdapi("/api/2.0/obms", action='put', payload=payload)
        if api_data['status']< 300:
            return True
    return False

def node_select():
    nodelist = []
    if NODEID != 'None':
        nodelist.append(NODEID)
        return nodelist
    else:
        catalog = rackhdapi('/api/2.0/nodes')
        if catalog['status'] != 200:
            print '**** Unable to retrieve node list via API.\n'
            sys.exit(255)
        for nodeentry in catalog['json']:
           if nodeentry['type'] == 'compute':
               nodelist.append(nodeentry['id'])
    if VERBOSITY >= 6:
        print "Node List:"
        print nodelist, '\n'
    if len(nodelist) == 0:
        print '**** Empty node list.\n'
    return nodelist


ARG_PARSER = argparse.ArgumentParser(description="Command Help")
ARG_PARSER.add_argument("-user", default="None",help="User Name, default:None")
ARG_PARSER.add_argument("-password", default="None",help="Password, default:None")
ARG_PARSER.add_argument("-ora", default="localhost",help="Specify RackHD ora IP address, default:localhost")
ARG_PARSER.add_argument("-v", default=0,type=int,help="Verbosity level of console output, default:0")
ARG_PARSER.add_argument("-nodeid", default="None",help="You can specify one node to apply OBM setting, add Node ID here, default:None")
ARG_PARSER.add_argument("-auth", default="off",choices=["off","on"],help="Specify if authentication is on , default:off")

CMD_ARGS = vars(ARG_PARSER.parse_args())
arg_username= CMD_ARGS["user"]
arg_password=CMD_ARGS["password"]
arg_ora=CMD_ARGS["ora"]
VERBOSITY=CMD_ARGS["v"]
NODEID=CMD_ARGS["nodeid"]

if CMD_ARGS["auth"]=="off":
    API_PORT =  str(OBM_CONFIG['ports']['http'])
    API_PROTOCOL =  'http'
else:
    API_PORT = str(OBM_CONFIG['ports']['https'])
    API_PROTOCOL = "https"
AUTH_TOKEN = "None"
REDFISH_TOKEN = "None"

if arg_ora=="localhost":
    print "Attention, you ora is on localhost! you can use -ora to specify ora ip"
    time.sleep(5)
shell_response= os.system("ping -c 1 " + arg_ora )

#and then check the response...
if shell_response == 0:
  print arg_ora, 'is up!'
else:
  print arg_ora, 'is down! Please check you network config!'
  exit(1)

NODECATALOG = node_select()

for NODE in NODECATALOG:
    if rackhdapi('/api/2.0/nodes/' + NODE)['json']['name'] != "Management Server":
        print 'Checking OBM setting on node :'+NODE
        node_obm= rackhdapi('/api/2.0/nodes/'+NODE)['json']['obms']
        if node_obm==[]:
           assert apply_obmsetting(NODE) is True,"Fail to apply obm setting!"
           #Verify the OBM setting
           node_obm_check = rackhdapi('/api/2.0/nodes/' + NODE)['json']['obms']
           if node_obm_check==[]:
               print "Fail to apply OBM setting on Node: "+ NODE
           else:
               print "Successfully set OBM setting on Node: " + NODE
        else:
            print "Node "+NODE+" already have OBM setting."