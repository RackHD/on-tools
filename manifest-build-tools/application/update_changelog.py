#!/usr/bin/env python
# Copyright 2015-2016, EMC, Inc.

"""
The script update changelog under debian

usage:
./on-tools/manifest-build-tools/HWIMO-BUILD on-tools/manifest-build-tools/application/update_changelog.py \
--build-dir d/ \
--version 1.2.6 \
--publish \
--git-credential https://github.com,GITHUB \
--message "new branch 1.2.6"

The required parameters: 
build-dir: The top directory which stores all the cloned repositories
version: The new release version
git-credential: url, credentials pair for the access to github repos.

The optional parameters:
message (default value is "new release" + version )
publish: If true, the updated changlog will be push to github.
git-credential: url, credentials pair for the access to github repos.
                If publish is true, the parameter is required.
"""
import os
import sys
import argparse
import datetime
import subprocess
from RepositoryOperator import RepoOperator
from common import *

class ChangelogUpdater(object):
    def __init__(self, repo_dir, version):
        """
        The module updates debian/changelog under the directory of repository
        __repo_dir: the directory of the repository
        __version: the new version which is going to be updated to changelog
        """
        self._repo_dir = repo_dir
        self._version = version
        self.repo_operator = RepoOperator()
 
    def debian_exist(self):
        """
        check whether debian or debianstatic directory under the repository
        return: True if debian or debianstatic exist
                False
        """
        if os.path.isdir(self._repo_dir):
            for filename in os.listdir(self._repo_dir):
                if filename == "debian":
                    return True
        return False

    def get_repo_name(self):
        """
        get the name of the repository
        :return: the name of the repository
        """
        repo_url = self.repo_operator.get_repo_url(self._repo_dir)
        repo_name = strip_suffix(os.path.basename(repo_url), ".git")
        return repo_name

    def update_changelog(self, message=None):
        """
        and an entry to changelog
        :param message: the message which is going to be added to changelog
        return: Ture if changelog is updated
                False, otherwise
        """
        repo_name = self.get_repo_name()
        if repo_name == "on-http":
            link_dir("debianstatic/on-http/", "debian", self._repo_dir)

        if not self.debian_exist():
            return False

        print "start to update changelog of {0}".format(self._repo_dir)
        cmd_args = ["dch", "-v", self._version, "-m"]
        if message is None:
            message = "new release {0}".format(self._version)
        cmd_args += ["-p", message]
        proc = subprocess.Popen(cmd_args,
                                cwd=self._repo_dir,
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                shell=False)
        (out, err) = proc.communicate()

        if repo_name == "on-http":
            os.remove(os.path.join(self._repo_dir, "debian"))

        if proc.returncode != 0:
            raise RuntimeError("Failed to add an entry for {0} in debian/changelog due to {1}".format(self._version, err))

        return True

def parse_command_line(args):
    """
    Parse script arguments.
    :return: Parsed args for assignment
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir",
                        required=True,
                        help="Top level directory that stores all the cloned repositories.",
                        action="store")
    parser.add_argument("--version",
                        required=True,
                        help="the new release version",
                        action="store")
    parser.add_argument("--message",
                        help="the message which is going to be added to changelog",
                        action="store")

    parser.add_argument("--publish",
                        help="Push the new manifest to github",
                        action='store_true')
    parser.add_argument("--git-credential",
                        help="Git credential for CI services",
                        action="append")

    parsed_args = parser.parse_args(args)
    return parsed_args

def main():
    # parse arguments
    args = parse_command_line(sys.argv[1:])
    if args.publish:
        if args.git_credential:
            repo_operator = RepoOperator(args.git_credential)
        else:
            print "If you want to publish the updated changelog, please specify the git-credential. Exiting now..."
            sys.exit(1)

    if os.path.isdir(args.build_dir):
        for filename in os.listdir(args.build_dir):
            try:
                repo_dir = os.path.join(args.build_dir, filename)
                updater = ChangelogUpdater(repo_dir, args.version)
                if updater.update_changelog(message = args.message):
                    if args.publish:
                        commit_message = "update changelog for new release {0}".format(args.version)
                        repo_operator.push_repo_changes(repo_dir, commit_message)
            except Exception,e:
                print "Failed to update changelog of {0} due to {1}".format(filename, e)
                sys.exit(1)
    else:
        print "The argument build-dir must be a directory"
        sys.exit(1)

if __name__ == "__main__":
    main()
    sys.exit(0)
