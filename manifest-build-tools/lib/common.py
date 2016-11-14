# Copyright 2016, EMC, Inc.

import subprocess
import logging

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

def link_dir(src, dest, dir):
    cmd_args = ["ln", "-s", src, dest]
    proc = subprocess.Popen(cmd_args,
                            cwd=dir,
                            stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            shell=False)
    (out, err) = proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError("Failed to sync {0} to {1} due to {2}".format(src, dest, err))


