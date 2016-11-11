# Copyright 2015, EMC, Inc.

"""
Module to abstract Git commands from within a program, by using the git command line

Credentials and identity information can be added to these jobs as needed.

"""

import os
import subprocess
import tempfile
from urlparse import urlparse


class GitBit(object):
    @staticmethod
    def __parse_credential_variable(varname):
        """
        Get the specified variable name from the environment and split it into username,password
        :param varname: environment variable name
        :return: username, password tuple
        """
        credential = os.environ[varname]

        (username, password) = credential.split(':', 2)
        return username, password


    def __init__(self, verbose=False):
        """
        Create a GitBit interface object

        :return:
        """
        self.__credentials = []
        self.__credential_filename = None
        self.__username = None
        self.__email = None
        self.__git_executable = "/usr/bin/git"

        self.__verbose = verbose


    def __del__(self):
        self.cleanup()


    def cleanup(self):
        """
        Cleans up the temporary file created by this object.

        :return:
        """
        if self.__credential_filename is not None:
            if os.path.exists(self.__credential_filename):
                os.remove(self.__credential_filename)
                self.__credential_filename = None


    def add_credential(self, server_url, username, password):
        """
        Associate the given URL with the credentials specified as arguments

        :param server_url:  Git repository URL (or fragment; only the host is needed)
        :param username: the repository user name
        :param password: the user's password (or token string)
        :return:
        """
        parts = urlparse(server_url)
        if (username is not None) and (password is not None):
            full_url = "{0}://{1}:{2}@{3}".format(parts.scheme,
                                                  username,
                                                  password,
                                                  parts.netloc)
            self.__credentials.append({"scheme": parts.scheme,
                                       "host": parts.netloc,
                                       "username": username,
                                       "password": password,
                                       "url": full_url,
                                      })
            return True
        else:
            return False


    def add_credential_from_variable(self, server_url, env_var_name):
        """
        Associate the given URL with the credentials found from the environment

        :rtype: None
        :param server_url: a Git repository URL (or fragment; only the host is needed)
        :param env_var_name: environment variable name containing credentials
        :return: success of operation
        """
        if env_var_name in os.environ:
            (username, password) = self.__parse_credential_variable(env_var_name)
            return self.add_credential(server_url, username, password)
        else:
            return False


    def get_credentials(self):
        """
        Return a list of all known credentials
        :return:
        """
        return self.__credentials


    def __write_credential_file(self):
        """
        Write the known credentials to a file suitable for Git's store credential helper.
        The filename is saved for later removal, and is returned

        See git-credential-store(1) for details on the format
        :return:
        """
        if self.__credential_filename is None:
            (fd, filename) = tempfile.mkstemp()    # pylint: disable=unused-variable
            self.__credential_filename = filename

            with open(filename, "w") as credential_file:
                for credential in self.get_credentials():
                    print >> credential_file, "{0}".format(credential['url'])


    def set_identity(self, username, email):
        """
        Define a username and email for the Git identity.  Git will autogenerate one as it can
        if not provided.  As our automated Git tools should not have a persistent identity via
        $HOME, we need to provide this in the tool.

        :param username:
        :param email:
        :return:
        """
        self.__username = username
        self.__email = email


    def run(self, args, directory=None, dry_run=False):
        """
        Run a Git command, with the arguments specified in args.

        Authentication information (if available) will be added to the command line

        :return: exit code,stdout,stderr: exit code, standard out and standard err
        :rtype: object
        :param args: the desired git command and arguments
        :param directory: the desired working directory (used via -C), None for cwd
        """
        config_args = []

        if directory is not None:
            config_args += ["-C", directory]

        if len(self.get_credentials()) > 0:
            self.__write_credential_file()
            config_args += ["-c", "credential.helper=store --file {0}".format(self.__credential_filename)]

        if self.__username is not None:
            config_args += ["-c", "user.name={0}".format(self.__username)]

        if self.__email is not None:
            config_args += ["-c", "user.email={0}".format(self.__email)]

        # get rid of the warning message
        config_args += ["-c", "push.default=simple"]

        # git should be found via the command line
        cmd_args = [self.__git_executable] + config_args + args

        if dry_run or self.__verbose:
            print "GIT: {0}".format(" ".join(cmd_args))

        if dry_run:
            return 0, None, None

        try:
            proc = subprocess.Popen(cmd_args,
                                    stderr=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    shell=False)
            (out, err) = proc.communicate()
        except subprocess.CalledProcessError as ex:
            return ex.returncode, None, None

        return proc.returncode, out, err
