#!/usr/bin/env python
# see http://stackoverflow.com/questions/1783405/checkout-remote-git-branch
# and http://stackoverflow.com/questions/791959/download-a-specific-tag-with-git

# check out a set of repositories to match the manifest file

# Copyright 2015-2016, EMC, Inc.

"""
usage:
./on-tools/manifest-build-tools/HWIMO-BUILD on-tools/manifest-build-tools/application/reprove.py \
--manifest manifest-files/rackhd-devel \
--builddir d \
--force \
--git-credential https://github.com,GITHUB \
--jobs 8 \
checkout
"""

import argparse
import json
import os
import shutil
import sys

import config

from urlparse import urlparse, urlunsplit
from RepositoryOperator import RepoOperator
from manifest import Manifest
from common import *

class ManifestActions(object):
    """
    valid actions:
    checkout: check out a set of repositories to match the manifest file
    """
    valid_actions = ['checkout']

    def __init__(self, manifest_path, builddir):
        """
        __force - Overwrite a directory if it exists
        __git_credential - url, credentials pair for the access to github repos
        __manifest - Repository manifest contents
        __builddir - Destination for checked out repositories
        __tagname - Tagname to be applied to all repos
        :return:
        """
        self._force = False
        self._git_credentials = None
        self._builddir = builddir
        self._manifest = None
        self.handle_manifest(manifest_path)
        self._jobs = 1
        self.actions = []
        
        self.repo_operator = RepoOperator()
 

    def set_force(self, force):
        """
        Standard setter for force
        : return: None
        """
        self._force = force
    def get_force(self):
        """
        Standard getter for git_credentials
        : return: force
        """
        return force

    def set_git_credentials(self, git_credential):
        """
        Standard setter for git_credentials
        : return: None
        """
        self._git_credentials = git_credential
        self.repo_operator.setup_gitbit(credentials=self._git_credentials)    


    def get_manifest(self):
        """
        Standard getter for manifest
        :return: None
        """
        return self._manifest


    def set_tagname(self, tagname):
        """
        Standard setter for tagname
        : return: None
        """
        self._tagname = tagname

    def get_tagname(self):
        """
        Standard getter for tagname
        : return: tag name
        """
        return self._tagname


    def add_action(self, action):
        if action not in self.valid_actions:
            print "Unknown action '{0}' requested".format(action)
            print "Valid actions are:"
            for op in self.valid_actions:
                print "  {0}".format(op)
            sys.exit(1)
        else:
            self.actions.append(action)


    def set_jobs(self, jobs):
        """
        Standard setter for jobs
        : return: None
        """
        self._jobs = jobs
        if self._jobs < 1:
            print "--jobs value must be an integer >=1"
            sys.exit(1)

    def handle_manifest(self, manifest_path):
        # and then finally do some actual work, which might depend upon the command line
        # option values

        try:
            self._manifest = Manifest(manifest_path)
            self._manifest.validate_manifest()
        except KeyError as error:
            print "Failed to create a Manifest instance for the manifest file {0} \nERROR:\n{1}"\
                  .format(manifest_path, error.message)
            sys.exit(1)
         
        for repo in self._manifest.get_repositories():
            repo['directory-name'] = self.directory_for_repo(repo)


    def check_builddir(self):
        """
        Checks the given builddir name and force flag. Deletes exists directory if one already
        exists and --force is set
        :return: None
        """
        if os.path.exists(self._builddir):
            if self._force:
                shutil.rmtree(self._builddir)
                print "Removing existing data at {0}".format(self._builddir)
            else:
                print "Unwilling to overwrite destination builddir of {0}".format(self._builddir)
                sys.exit(1)

        os.makedirs(self._builddir)

        
    def get_repositories(self):
        """
        Issues checkout commands to dictionaries within a provided manifest
        :return: None
        """
        repo_list = self._manifest.get_repositories()
        try:
            self.repo_operator.clone_repo_list(repo_list, self._builddir, jobs=self._jobs)
        except RuntimeError as error:
            print "Exiting due to error: {0}".format(error)
            sys.exit(1)
            

    def directory_for_repo(self, repo):
        if 'checked-out-directory-name' in repo:
            repo_directory = repo['checked-out-directory-name']
        else:
            if 'repository' in repo:
                repo_url = repo['repository']
                repo_directory = strip_suffix(os.path.basename(repo_url), ".git")
            else:
                raise ValueError("no way to find basename")

        repo_directory = os.path.join(self._builddir, repo_directory)
        return repo_directory



def parse_command_line(args):
    """
    Parse script arguments.
    :return: Parsed args for assignment
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest",
                        required=True,
                        help="repository manifest file",
                        action="store")
    parser.add_argument("--builddir",
                        required=True,
                        help="destination for checked out repositories",
                        action="store")
    parser.add_argument("--force",
                        help="use destination dir, even if it exists",
                        action="store_true")
    parser.add_argument("--git-credential",
                        help="Git credentials for CI services",
                        action="append")
    parser.add_argument("--jobs",
                        default=1,
                        help="Number of parallel jobs to run",
                        type=int)
    parser.add_argument('action',
                        nargs="+")

    parsed_args = parser.parse_args(args)
    return parsed_args


def main():
    # parse arguments
    args = parse_command_line(sys.argv[1:])
    
    manifest_actions = ManifestActions(args.manifest, args.builddir)

    if args.force:
        manifest_actions.set_force(args.force)

    for action in args.action:
        manifest_actions.add_action(action)

    if args.git_credential:
        manifest_actions.set_git_credentials(args.git_credential)

    if args.jobs:
        manifest_actions.set_jobs(args.jobs)

    if 'checkout' in manifest_actions.actions:
        manifest_actions.check_builddir()
        manifest_actions.get_repositories()


if __name__ == "__main__":
    main()
    sys.exit(0)
