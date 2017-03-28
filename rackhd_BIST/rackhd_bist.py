#!/usr/bin/env python

# Copyright 2017, Dell EMC, Inc.
# -*- coding: UTF-8 -*-

"""
    RackHD built-in self-test script.
    This script will run some tests to check RackHD configurations and RackHD running environment
    health status. RackHD BIST tests include:
        1. RackHD services start/stop and heartbeat signals monitoring
        2. RackHD required services status check
        3. RackHD required tools version check
        4. RackHD required static file existence check
        5. RackHD configuration file validation
        6. Optional APIs GET tests
        7. Hardware resources check
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

    # RackHD BIST test suites in sequence
    bist_test_suites = ["StaticFiles", "Tools",
                        "RequiredServices", "HardwareResource",
                        "RackhdConfigure", "RackhdServices",
                        "RackhdAPI"]
    print "\nStarting RackHD built-in self-test..."

    if arg_list.path:
        test_suites.CONFIGURATION["sourceCodeRepo"] = arg_list.path

    for test_suite in bist_test_suites:
        test_suites.Logger.print_test_suite_name("\n" + test_suite + "\n")
        test_class = getattr(test_suites, test_suite)
        test_class().run_test()

    if not arg_list.start: # RackHD services will be stopped default
        test_suites.Logger.print_test_suite_name("\nRackHDStop\n")
        test_suites.RackhdServices().stop_rackhd_services()

    print "\nRackHD built-in self-test completed!"
