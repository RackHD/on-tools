import sys
import os
from manipulator import Manipulator

# pylint: disable=no-name-in-module

if __name__ == '__main__':

    for arg in sys.argv[1:]:

        if arg.find('--getdir') == 0:
            print Manipulator().get_data_path()
            run_test = False

        elif arg.find('--start') == 0:
            Manipulator().start()
            run_test = False

        elif arg.find('--stop') == 0:
            Manipulator().stop()
            run_test = False
