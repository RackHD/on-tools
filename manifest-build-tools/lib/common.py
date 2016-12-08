# Copyright 2016, EMC, Inc.

import subprocess
import logging
from pyjavaproperties import Properties
import os

log_file = 'manifest-build-tools.log'
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename=log_file, filemode='w', level=logging.DEBUG)

def strip_suffix(text, suffix):
    """
    Cut a set of the last characters from a provided string
    :param text: Base string to cut
    :param suffix: String to remove if found at the end of text
    :return: text without the provided suffix
    """
    if text is not None and text.endswith(suffix):
        return text[:len(text) - len(suffix)]
    else:
        return text

def strip_prefix(text, prefix):
    if text is not None and text.startswith(prefix):
        return text[len(prefix):]
    else:
        return text

def write_parameters(filename, params):
    """
    Add/append parameters(java variable value pair) to the given parameter file.
    If the file does not exist, then create the file.
    :param filename: The path of the parameter file
    :param params: the parameters dictionary
    :return:None on success
            Raise any error if there is any
    """
    if filename is None:
        raise ValueError("parameter file name is not None")
    with open(filename, 'w') as fp:
        for key in params:
            entry = "{key}={value}\n".format(key=key, value=params[key])
            fp.write(entry)

def link_dir(src, dest, dir):
    cmd_args = ["ln", "-s", src, dest]
    run_command(cmd_args, directory=dir)

def get_debian_version(file_path):
    """
    Get the version of a debian file
    :param file_path: the path of the debian file
    :return: the version of the debian file
    """
    cmd_args = ["dpkg-deb", "-f", file_path, "Version"]
    debian_version = run_command(cmd_args)
    return debian_version

def get_debian_package(file_path):
    cmd_args = ["dpkg-deb", "-f", file_path, "Package"]
    debian_name = run_command(cmd_args)
    return debian_name

def parse_property_file(filename):
    """
    parse java properties file
    :param filename: the path of the properties file
    :return: dictionary loaded from the file
    """
    if not os.path.isfile(filename):
        raise RuntimeError("No file found for parameter at {0}".format(filename))
    p = Properties()
    p.load(open(filename))
    return p

def parse_credential_variable(varname):
    """
    Get the specified variable name from the environment and split it into username,password
    :param varname: environment variable name
    :return: username, password tuple
    """
    try:
        if varname not in os.environ:
            raise ValueError("Credential variable {0} doesn't exist".format(varname))

        credential = os.environ[varname]
        if credential is None:
            raise ValueError("Failed to parse credential variable {0}".format(varname))

        (username, password) = credential.split(':', 2)
        if username is None or password is None:
            raise ValueError("Failed to split credential variable {0} into username, password".format(varname))

        return username, password
    except Exception, e:
        raise ValueError(e)

def run_command(cmd_args, directory=None):
    proc = subprocess.Popen(cmd_args,
                            stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            cwd=directory,
                            shell=False)
    (out, err) = proc.communicate()
    if proc.returncode == 0:
        return out.strip()
    else:
        commandline = " ".join(cmd_args)
        raise RuntimeError("Failed to run command {0} due to {1}".format(commandline, err))

def find_specify_type_files(directory, suffix, depth=4096):
    file_list = []
    top_dir_depth = directory.count(os.path.sep) #How deep is at starting point
    for root, dirs, files in os.walk(directory):
        root_depth = root.count(os.path.sep)
        if (root_depth - top_dir_depth) <= depth:
            for file_itr in files:
                if file_itr.endswith(suffix):
                    abs_file = os.path.abspath(os.path.join(root, file_itr))
                    file_list.append(abs_file)
    return file_list

def str2bool(string):
    if string.lower() in ("true", "yes", "t", "1"):
        return True
    else:
        return False

