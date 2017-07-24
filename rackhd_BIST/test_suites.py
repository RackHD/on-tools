#!/usr/bin/env python

# Copyright 2017, Dell EMC, Inc.
# -*- coding: UTF-8 -*-

"""
    RackHD built-in self-test suites
    This document includes RackHD BIST test suites
"""

import os
import re
import json
import sys
import httplib
import pika
import test_utils as utils

CONFIGURATION = utils.CONFIGURATION
Logger = utils.Logger()


class RackhdServices(object):
    """
    RackHD services test suite
    """
    def __init__(self):
        self.source_code_path = CONFIGURATION.get("sourceCodeRepo")
        self.is_regular_repo = (self.source_code_path == "/var/renasar") or (
            self.source_code_path == "/var/renasar/")
        self.services = CONFIGURATION.get("rackhdServices")
        self.heartbeat_unavailable_flags = self.services[:]
        self.amqp_address = {"host": "localhost", "port": 5672}
        self.amqp_connect_timeout = 20
        self.amqp_connection = {}

    def __get_version_from_dpkg(self, service):
        """
        Check RackHD version from 'dpkg -l' output
        """
        # dpkg -l output example:
        #   ii  on-http 2.0.0-20170316UTC-25c81ec  amd64  RackHD HTTP engine service
        cmd = ["dpkg -l | grep {} | awk '{{print $3}}'".format(service)]
        result = utils.robust_check_output(cmd=cmd, shell=True)
        if not result["message"]:
            result["exit_code"] = -1
        return result

    def __get_version_from_commitstring(self, service):
        """
        Check RackHD version from commitstring.txt file
        """
        commitStringPath = os.path.join(self.source_code_path, service, "commitstring.txt")
        result = utils.robust_open_file(commitStringPath)
        return result

    def __get_version_from_package(self, service):
        """
        Check RackHD version from package.json file
        """
        package_file_path = os.path.join(self.source_code_path, service, "package.json")
        result = utils.robust_load_json_file(package_file_path)
        version = result["message"].get("version")
        if not result["exit_code"] and version:
            result["message"] = version
        return result

    def check_service_version(self):
        """
        Check RackHD version
        """
        for service in self.services:
            description = "Check service {} version".format(service)
            if self.is_regular_repo:
                result = self.__get_version_from_dpkg(service)
                if result["exit_code"]:  # if failed to get version from dpkg, try commitstring
                    result = self.__get_version_from_commitstring(service)
            else:
                result = self.__get_version_from_package(service)
            Logger.record_command_result(description, "warning", result)

    def __operate_regular_rackhd(self, operator):
        """
        Start or stop RackHD services from regular RackHD code repo /var/renasar/
        :param operator: operator for RackHD service, should be "start" or "stop"
        """
        for service in self.services:
            description = "{} RackHD service {}".format(operator.capitalize(), service)
            cmd = ["service", service, operator]
            result = utils.robust_check_output(cmd)
            if not result["exit_code"]:
                result["message"] = ""
            Logger.record_command_result(description, 'error', result)

    def __get_pid_executing_path(self, pid):
        """
        Get Linux pid executing path
        :param pid: Linux process id
        :return: pid executing path string, an example: "/home/onrack/src/on-http"
        """
        # ls -l /proc/<pid> output example
        # lrwxrwxrwx 1 root root   0 Mar 28 14:11 cwd -> /home/onrack/src/on-http
        cmd = ["sudo ls -l /proc/{0} | grep cwd | awk '{{print $NF}}'".format(pid)]
        output = utils.robust_check_output(cmd, shell=True)
        return output["message"].strip("\n")

    def __stop_user_rackhd(self):
        """
        Stop RackHD services from user provided RackHD code repo
        """
        get_pid_cmd = ['ps aux | grep node | sed "/grep/d"| ' \
                            'sed "/sudo/d" | awk \'{print $2}\' | sort -r -n']
        output = utils.robust_check_output(cmd=get_pid_cmd, shell=True)
        process_list = output["message"].strip("\n").split("\n")
        for pid in process_list:
            pid_service_name = self.__get_pid_executing_path(pid).split("/")[-1]
            if pid_service_name not in self.services:
                continue
            kill_pid_cmd = ["kill", "-9", pid]
            result = utils.robust_check_output(kill_pid_cmd)
            description = "Stop RackHD service {}".format(pid_service_name)
            Logger.record_command_result(description, 'error', result)

    def __start_user_rackhd(self):
        """
        Start RackHD services from user provided RackHD code repo
        """
        for service in self.services:
            description = "Start RackHD service {}".format(service)
            os.chdir(os.path.join(self.source_code_path, service))
            cmd = ["node index.js > /dev/null 2>&1 &"]  # RackHD services need run in background
            result = utils.robust_check_output(cmd=cmd, shell=True)
            Logger.record_command_result(description, 'error', result)

    def start_rackhd_services(self):
        """
        Start RackHD Services
        """
        if self.is_regular_repo:
            self.__operate_regular_rackhd("start")
        else:
            self.__start_user_rackhd()

    def stop_rackhd_services(self):
        """
        Stop RackHD Services
        """
        if self.is_regular_repo:
            self.__operate_regular_rackhd("stop")
        else:
            self.__stop_user_rackhd()

    def __close_amqp_connection(self):
        """
        Close AMQP connection
        """
        self.amqp_connection["channel"].stop_consuming
        self.amqp_connection["connection"].close()

    def __amqp_timeout_callback(self):
        """
        AMQP connection timeout handling
        """
        self.__close_amqp_connection()
        description = "Connection to AMQP channels timeout"
        details = "Can't receive heartbeat messages from services {}".format(
            ", ".join(self.heartbeat_unavailable_flags))
        Logger.record_log_message(description, "error", details)

    def run_heartbeat_test(self):
        """
        Initiate AMQP to monitor hearbeat messages
        """
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.amqp_address["host"],
                port=self.amqp_address["port"]
            ))
        channel = connection.channel()
        result = channel.queue_declare(exclusive=True)
        queue_name = result.method.queue
        channel.queue_bind(exchange="on.events", queue=queue_name,
                           routing_key="heartbeat.updated.information.#")
        connection.add_timeout(self.amqp_connect_timeout, self.__amqp_timeout_callback)
        self.amqp_connection["channel"] = channel
        self.amqp_connection["connection"] = connection
        # print "Waiting for RackHD services heartbeat signals..."
        try:
            for method_frame, properties, body in channel.consume(queue_name):
                channel.basic_ack(method_frame.delivery_tag)
                service = method_frame.routing_key.split('.')[-1]
                if service in self.heartbeat_unavailable_flags:
                    self.heartbeat_unavailable_flags.remove(service)
                    description = "Received heartbeat signal from RackHD service {}".format(service)
                    Logger.record_log_message(description, "debug", "")
                if not self.heartbeat_unavailable_flags:
                    self.__close_amqp_connection()
                    break
        except pika.exceptions.ConnectionClosed:
            description = "Failed to connection to AMQP channels"
            Logger.record_log_message(description, "error", "")

    def run_test(self):
        """
        Run tests for RackhdServices
        """
        self.check_service_version()
        self.start_rackhd_services()
        self.run_heartbeat_test()


class RequiredServices(object):
    """
    RackHD required services test suite
    """
    def __init__(self):
        self.services = CONFIGURATION.get("requiredServices")
        self.dhcp_config_file = "/etc/dhcp/dhcpd.conf"
        self.dhcp_ip_range = {"start_ip": '', "end_ip": ''}
        self.dhcp_rackhd_config = {
            "subnet": 'subnet 172\.31\.128\.0 netmask 255\.255\.\d{3}\.0\s*{' \
                '.*(range (172\.31\.\d{1,3}\.\d{1,3}) (172\.31\.\d{1,3}\.\d{1,3}))+;' \
                '.*option vendor-class-identifier "PXEClient";' \
                '.*}',
            "ignore-client-uids": 'ignore-client-uids.*true;',
            "deny duplicates": 'deny.*duplicates;'
        }

    def check_service_process(self):
        """
        Check RackHD required services running status
        """
        for service in self.services:
            cmd = ["service", service, "status"]
            result = utils.robust_check_output(cmd)
            description = "Check service {} running status".format(service)
            if result["exit_code"] == 0:
                output = result["message"]
                if output.find("running") == -1:
                    result["exit_code"] = -1
                else:
                    result["message"] = ""  # message is not necessary for successful service
            Logger.record_command_result(description, "error", result)

    def get_dhcp_ip_count(self):
        """
        Get IP count that RackHD dhcp can support
        """
        if not (self.dhcp_ip_range["start_ip"] and self.dhcp_ip_range["end_ip"]):
            description = "Cann't get maximum IP count supported by DHCP configure"
            Logger.record_log_message(description, "warning", "")
            return
        begin_ip_bits = self.dhcp_ip_range["start_ip"].split('.')
        end_ip_bits = self.dhcp_ip_range["end_ip"].split('.')
        ip_count = 0
        for begin, end in zip(begin_ip_bits, end_ip_bits):
            ip_count = ip_count*256 + int(end) - int(begin)
        description = "Maximum IP count supported by DHCP configure is {}".format(ip_count + 1)
        Logger.record_log_message(description, "info", "")

    def validate_dhcp_config(self):
        """
        Validate RackHD required dhcpd configurations
        """
        dhcp_config = utils.robust_open_file(self.dhcp_config_file)
        if dhcp_config["exit_code"] != 0:
            description = "Can't open {}".format(self.dhcp_config_file)
            Logger.record_command_result(description, "error", dhcp_config)
            return

        # Convert useful configures to a string
        valid_config_lines = []
        for line in dhcp_config["message"]:
            line = line.strip(" ").strip("\n")
            if not line.startswith("#") and line:
                valid_config_lines.append(line)
        valid_config_string = "".join(valid_config_lines)

        # Check RackHD required configure lines
        unconfig_keys = self.dhcp_rackhd_config.keys()
        subnet_match = []
        for key, value in self.dhcp_rackhd_config.items():
            match = re.compile(value).search(valid_config_string)
            if match:
                unconfig_keys.remove(key)
                if key == "subnet":  # Get DHCP IP Range for IP count calculation
                    subnet_match = match.groups()
                    self.dhcp_ip_range["start_ip"] = subnet_match[1]
                    self.dhcp_ip_range["end_ip"] = subnet_match[2]
        if not unconfig_keys:
            description = "RackHD required dhcpd configure is correct"
            Logger.record_log_message(description, "debug", "")
        else:
            for value in unconfig_keys:
                description = "RackHD required dhcpd configure {} is incorrect".format(value)
                Logger.record_log_message(description, "error", "")

    def run_test(self):
        """
        Run RackHD required service tests
        """
        self.validate_dhcp_config()
        self.get_dhcp_ip_count()
        self.check_service_process()


class RackhdConfigure(object):
    """
    RackHD configuration test suite
    """
    def __init__(self):
        self.template_file_path = "./rackhd_config_template.json"
        self.log_level = {
            "required": {
                "missing": "error",
                "unequal": "warning"
            },
            "optional": {
                "missing": "warning",
                "unequal": "warning"
            }
        }
        self.config_file_paths = CONFIGURATION.get("configFile")
        self.rackhd_config_template = {}
        self.rackhd_config = {}
        self.unchecked_configs = []

    def load_config_file(self):
        """
        Load RackHD configures
        """
        for path in self.config_file_paths:
            result = utils.robust_load_json_file(path)
            if not result["exit_code"]:
                self.rackhd_config = result["message"]
                self.unchecked_configs = self.rackhd_config.keys()
                result["message"] = ""
                break
        description = "Load RackHD configure file"
        Logger.record_command_result(description, "error", result)

    def load_config_template(self):
        """
        Load RackHD configure template file
        """
        result = utils.robust_load_json_file(self.template_file_path)
        if result["exit_code"]:
            description = "Load RackHD configure file {}".format(self.template_file_path)
            Logger.record_command_result(description, "error", result)
        else:
            self.rackhd_config_template = result["message"]

    def validate_config_via_key(self, template_key):
        """
        Validate content of RackHD configure file against configure template key
        :param template_key: keys in configure template
        """
        template = self.rackhd_config_template.get(template_key)
        for key, value in template.items():
            config = self.rackhd_config.get(key)
            if config is None:
                description = "RackHD configuration item {} is not specified".format(key)
                Logger.record_log_message(
                    description, self.log_level[template_key]["missing"], '')
                continue
            self.unchecked_configs.remove(key)
            if value == "":  # value is empty means we don't care value of this items
                pass
            elif config != value:
                description = "RackHD configuration item {} is not typical value".format(key)
                details = "Typical value: {0}, User value: {1}".format(value, config)
                Logger.record_log_message(
                    description, self.log_level[template_key]["unequal"], details)
            else:
                description = "Check RackHD configuration item {}".format(key)
                Logger.record_log_message(description, 'debug', '')

    def validate_config_items(self):
        """
        Validate RackHD configure files against configure template
        """
        for key in self.rackhd_config_template.keys():
            self.validate_config_via_key(key)

    def logging_extra_items(self):
        """
        Record extra items besides template items
        """
        for key in self.unchecked_configs:
            description = "Configuration item {} is specified".format(key)
            details = '{}: {}'.format(key, self.rackhd_config.get(key))
            Logger.record_log_message(description, "info", details)

    def run_test(self):
        """
        Rackhd configure tests
        """
        self.load_config_file()
        self.load_config_template()
        if not self.rackhd_config_template:
            return -1
        if not self.rackhd_config:
            print "Can't find or load RackHD configuration files, existing tests"
            sys.exit(-1)  # Without configuration, RackHD services and APIs can't work
        self.validate_config_items()
        self.logging_extra_items()


class Tools(object):
    """
    RackHD required tools test suite
    """
    def __init__(self):
        self.tools = CONFIGURATION.get("toolList")

    def validate_requirement(self, requirement, real_version):
        """
        Validate tool version
        :param requirement: an object includes tool version requirement,
            it may contains none or any of below items
            min: required minimum version
            max: required maximum version
            among: version should be among a list
            exclusive: version should not be any of a list
        :param version: tool version got
        :return: Boolean value, True for valid version False for invalid version
        """
        version_validate_result = {
            "min": # version should larger than min, smaller than min will give False
                utils.tool_version_compare(real_version, requirement.get("min", None)) == 1,
            "max": # version should smaller than max, larger than max will give False
                utils.tool_version_compare(real_version, requirement.get("max", None)) == -1,
            "among": real_version in requirement.get("among", [real_version]),
            "exclusive": real_version not in requirement.get("exclusive", [])
        }
        for key, value in requirement.items():
            if not value and not version_validate_result[key]:
                return False
        return True

    def validate_tool_list(self):
        """
        Validate tools
        """
        for tool in self.tools:
            tool_name = tool.get("name")
            cmd = tool.get("getVersionCommand", [tool_name, "--version"])
            redirect_flag = tool.get("redirect", False)  # Flag for redirecting stderr to stdout
            isRequired = tool.get("isRequired", True) # By default tool is required
            description = "Check version for tool {}".format(tool_name)
            version_info = utils.get_tool_version(cmd, redirect_flag)
            if version_info["exit_code"] == 0:
                version_requirement = tool.get("version", {})
                is_valid = self.validate_requirement(version_requirement, version_info["message"])
                if not is_valid:
                    version_info["exit_code"] = -1
                    version_info["message"] = "Tool {} version is invalid".format(tool_name)
            if isRequired:
                level = "error"
            else:
                level = "warning"
            Logger.record_command_result(description, level, version_info)

    def run_test(self):
        """
        Run tool verification test
        """
        self.validate_tool_list()


class StaticFiles(object):
    """
    RackHD static files test suite
    """
    def __init__(self):
        self.source_code_path = CONFIGURATION["sourceCodeRepo"]
        self.requiredStaticFiles = CONFIGURATION["requiredStaticFiles"]
        self.optionalStaticFiles = CONFIGURATION.get("optionalStaticFiles", [])

    def check_files_existence(self, file_obj_list, log_level):
        """
        Check existence of files
        :param file_obj_list: static file object list, each file object should including
            file path and all static files under the file path
        :param log_level: log level if error happened
        """
        if not file_obj_list:
            return
        for file_obj in file_obj_list:
            file_path = os.path.join(self.source_code_path, file_obj.get("dirPath", ""))
            file_list = file_obj.get("fileList", [])
            for file_name in file_list:
                details = ''
                description = "Check existence of file {}".format(file_name)
                file_name = os.path.join(file_path, file_name)
                if os.path.isfile(file_name):
                    level = "debug"
                    #description += " succeeded"
                    #details = "File {} exists".format(file_name)
                else:
                    level = log_level
                    description += " failed"
                    details = "File {} doesn't exist".format(file_name)
                Logger.record_log_message(description, level, details)

    def run_test(self):
        """
        Run static files test
        """
        self.check_files_existence(self.requiredStaticFiles, 'error')
        self.check_files_existence(self.optionalStaticFiles, 'warning')

class RackhdAPI(object):
    """
    RackHD southbound APIs test suite
    """
    def __init__(self):
        self.api_list = CONFIGURATION["apis"]
        self.http_method = "GET"
        self.http_config = {
            "host": "localhost",
            "port": 8080,
            "timeout": 10
        }
        self.get_sku_api = "/api/current/skus"

    def __initiate_rackhd_connect(self):
        """
        Initiate RackHD http connect
        """
        return httplib.HTTPConnection(host=self.http_config["host"],
                                      port=self.http_config["port"],
                                      timeout=self.http_config["timeout"])
   
 
    def send_http_request(self, http_connect, http_api):
        """
        Define a function to catch the errors of sending http request.
        Otherwise, it needs to catch errors many times.
        """

        try:
             http_connect.request(self.http_method, http_api)
             response = http_connect.getresponse()
             return response
        except:
            Logger.record_log_message("http request error", "error", "")
            return
             
     
    def get_supported_skus(self):
        """
        Get support skus
        """
        
        http_connect = self.__initiate_rackhd_connect()
        response = self.send_http_request(http_connect, self.get_sku_api)
        
        if response.status >= 500:
            Logger.record_log_message("Can't get SKUs", "info", "")
            return
        platforms = []
        body = json.loads(response.read())
        for data in body:
            if data.get("name"):
                platforms.append(data.get("name"))
        if platforms:
            description = "Injected RackHD SKUs: {}".format(" ,".join(platforms))
        else: 
            description = "No SKU is injected"
        Logger.record_log_message(description, "info", "")
        http_connect.close()
      
    def run_api_get_tests(self):
        """
        Run api GET tests for API list
        """
        for api in self.api_list:
           
            http_connect = self.__initiate_rackhd_connect()
            response = self.send_http_request(http_connect, api)
    
            if response.status >= 500:
                description = "Failed to GET API {}".format(api)
                Logger.record_log_message(description, "error", "")
            else:
                description = "Succeeded to GET API {}".format(api)
                Logger.record_log_message(description, "debug", "")
        http_connect.close()

    def run_test(self):
        """
        Run API tests
        """
        self.get_supported_skus()
        self.run_api_get_tests()

class HardwareResource(object):
    """
    RackHD hardware resource test suite
    """
    def __init__(self):
        self.memory_command = ["free", "-h"]
        self.cpu_command = ["lscpu"]
        self.disk_command = ["fdisk", "-l"]

    def get_cpu_info(self):
        """
        Get CPU information, command output example:
            CPU(s):                4
            CPU MHz:               2693.509
            L1d cache:             32K
            L1i cache:             32K
            L2 cache:              256K
            L3 cache:              20480K
        """
        result = utils.robust_check_output(self.cpu_command)
        info_list = result["message"].strip("\n").strip(" ").split("\n")
        cpu_info = {}
        for info in info_list:
            info = info.split(":")
            cpu_info[info[0].strip(" ")] = info[-1].strip(" ")
        description = "RackHD server CPU info: {} cores, {}MHz,".format(
            cpu_info["CPU(s)"], cpu_info["CPU MHz"])
        Logger.record_log_message(description, "info", "")
        return cpu_info

    def get_mem_info(self):
        """
        Get CPU information, command output first two lines example:
                        total       used       free     shared    buffers     cached
            Mem:           31G       8.8G        22G       4.1M       689M       6.3G
        """
        result = utils.robust_check_output(self.memory_command)
        info_list = result["message"].strip("\n").strip(" ").split("\n")
        title_list = info_list[0].strip(" ").split(" ")
        data_list = info_list[1].strip(" ").split(" ")
        title_list = [x for x in title_list if x]
        data_list = [x for x in data_list if x]
        del data_list[0]
        mem_info = {}
        for title, data in zip(title_list, data_list):
            mem_info[title] = data
        description = "RackHD server memory size: {}".format(mem_info["total"])
        Logger.record_log_message(description, "info", "")
        return mem_info

    def get_disk_capacity(self):
        """
        Get disk capacity, fdisk -l output first line example:
            Disk /dev/sda: 104.9 GB, 104857600000 bytes
        """
        result = utils.robust_check_output(self.disk_command, shell=False, redirect=True)
        info_list = result["message"].strip("\n").strip(" ").split("\n")
        capacity = ""
        for disk_info in info_list:
            pattern = re.compile("Disk /dev/sd[a-z]{1,3}:\s+(\d{0,5}\.?\d{0,3}\s+(T|G|M)i?B)", re.I)
            match = pattern.search(disk_info)
            if match:
                capacity = match.group(1)
                break
        description = "RackHD server disk capacity: {}".format(capacity)
        Logger.record_log_message(description, "info", "")
        return capacity

    def validate_resource(self):
        """
        Validate if RackHD server resource meet requirement:
        TODO: RackHD hardware requirement is not defined yet, this function should be updated if
        RackHD released hardware requirement
        """
        pass

    def run_test(self):
        """
        Run hardware resource tests
        """
        self.get_cpu_info()
        self.get_mem_info()
        self.get_disk_capacity()
        self.validate_resource()
