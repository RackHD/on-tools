#!/usr/bin/env python

# Copyright 2017, Dell EMC, Inc.
# -*- coding: UTF-8 -*-

"""
    RackHD built in self test script.
    This script will run some tests to check RackHD configurations and RackHD running environment
    health status.
"""

import argparse
import test_suites

parser = argparse.ArgumentParser(description='RackHD BIST arguments')
parser.add_argument('--path', action="store", dest="path", default="",
                    help="Specify RackHD source code path")
parser.add_argument('--start', action="store_true", dest="start", default=False,
                    help="Leave RackHD services in start status after BIST tests")
arg_list = parser.parse_args()

if __name__ == "__main__":

    print "Starting RackHD build in self test..."
    static_files = test_suites.StaticFiles(arg_list.path)
    tools = test_suites.Tools()
    rackhd_require_services = test_suites.RequiredServices()
    hardware_resource = test_suites.HardwareResource()
    configure_file = test_suites.RackhdConfigure()
    rackhd_services = test_suites.RackhdServices(arg_list.path)
    apis = test_suites.RackhdAPI()

    static_files.run_test()
    tools.run_test()
    rackhd_require_services.run_test()
    hardware_resource.run_test()
    configure_file.run_test()
    rackhd_services.run_test()
    apis.run_test()
    if not arg_list.start: # RackHD services will be stopped default
        rackhd_services.stop_rackhd_services()
    print "RackHD built in self test completed!"
