#!/usr/bin/env python
# see http://stackoverflow.com/questions/1783405/checkout-remote-git-branch
# and http://stackoverflow.com/questions/791959/download-a-specific-tag-with-git

# check out a set of repositories to match the manifest file

# Copyright 2015, EMC, Inc.

"""
usage:
./on-tools/manifest-build-tools/HWIMO-BUILD on-tools/manifest-build-tools/application/reprove.py \
--manifest manifest-files/rackhd-devel \
--builddir d \
--force \
--git-credential https://github.com,GITHUB \
--jobs 8 \
--branch-name "branch/release-1.5.1 \
checkout \
branch

The required parameters:
manifest: the path of manifest file.
builddir: the destination for checked out repositories.
git-credential: url, credentials pair for the access to github repos.
                For example: https://github.com,GITHUB
                GITHUB is an environment variable: 
                GITHUB=username:password
action: the supported action, includes checkout branch.
        "checkout": it  will clone all the repositories in a manifest file;
                    if "branch" in a repository dictionary, the action will check out to the branch.
                    if "commit-id" in a repository dictionary, the action will reset to the commit 
        "branch": it will create a new branch for all the repositories under builddir
                  and update the package.json to point to the new branch.
                  For example:
                  - git+https://github.com/RackHD/on-core.git
                  + git+https://github.com/RackHD/on-core.git#branch/release-1.2.3

The optional parameters:
force: use destination directory, even if it exists
jobs: number of parallel jobs to run. The number is related to the compute architecture, multi-core processors...
branch-name: the name of new branch.
             If action contains "branch", the parameter is required.
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
    valid_actions = ['checkout', 'branch', 'packagerefs']

    def __init__(self, manifest_path, builddir, force=False, git_credentials=None, jobs=1, actions=[], branch_name=None):
        """
        __force - Overwrite a directory if it exists
        __git_credential - url, credentials pair for the access to github repos
        __manifest - Repository manifest contents
        __builddir - Destination for checked out repositories
        __jobs - Number of parallel jobs to run
        __actions -Supported actions
        :return:
        """
        self._force = force
        self._git_credentials = git_credentials
        self._builddir = builddir
        self._manifest = None
        self.handle_manifest(manifest_path)
        self._jobs = jobs
        self.actions = []
        for action in actions:
            self.add_action(action)

        self._branch_name = branch_name
       
        self.repo_operator = RepoOperator(self._git_credentials)

    def set_force(self, force):
        """
        Standard setter for force
        :param force: if true, overwrite a directory if it exists
        :return: None
        """
        self._force = force

    def get_force(self):
        """
        Standard getter for git_credentials
        :return: force
        """
        return self._force

    
    def set_branch_name(self, branch):
        """
        Standard setter for force
        :param force: if true, overwrite a directory if it exists
        :return: None
        """
        self._branch_name = branch

    def get_branch_name(self):
        """
        Standard getter for git_credentials
        :return: force
        """
        return self._branch_name

    def set_git_credentials(self, git_credential):
        """
        Standard setter for git_credentials
        :param git_credential: url, credentials pair for the access to github repos
        :return: None
        """
        self._git_credentials = git_credential
        self.repo_operator.setup_gitbit(credentials=self._git_credentials)    

    def get_manifest(self):
        """
        Standard getter for manifest
        :return: an instance of Manifest
        """
        return self._manifest

    def add_action(self, action):
        """
        Add action to actions
        :param action: a string, just like: checkout
        :return: None
        """
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
        :param jobs: number of parallel jobs to run
        :return: None
        """
        self._jobs = jobs
        if self._jobs < 1:
            print "--jobs value must be an integer >=1"
            sys.exit(1)

    def handle_manifest(self, manifest_path):
        """
        initial manifest and validate it
        :param manifest_path: the path of manifest file
        :return: None
        """
        try:
            self._manifest = Manifest(manifest_path)
            self._manifest.validate_manifest()
        except KeyError as error:
            print "Failed to create a Manifest instance for the manifest file {0} \nERROR:\n{1}"\
                  .format(manifest_path, error.message)
            sys.exit(1)
         
        for repo in self._manifest.repositories:
            repo['directory-name'] = self.directory_for_repo(repo)

    def check_builddir(self):
        """
        Checks the given builddir name and force flag. 
        Deletes exists directory if one already exists and --force is set
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
        repo_list = self._manifest.repositories
        try:
            self.repo_operator.clone_repo_list(repo_list, self._builddir, jobs=self._jobs)
        except RuntimeError as error:
            print "Exiting due to error: {0}".format(error)
            sys.exit(1)
            
    def directory_for_repo(self, repo):
        """
        Get the directory of a repository
        :param repo: a dictionary
        :return: the directary of repository
        """
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

    def execute_actions(self):
        """
        start to execute actions
        :return: None
        """
        # Start to check out a set of repositories within a manifest file
        if 'checkout' in self.actions:
            self.check_builddir()
            self.get_repositories()

        # Start to create branch and update package.json
        if 'branch' in self.actions:
            self.execute_branch_action()

        # Start to update the packge.json, for example:
        # - git+https://github.com/RackHD/on-core.git
        # +     
        if 'packagerefs' in self.actions:
            self.update_package_references()

    def execute_branch_action(self):
        """
        execute the action "branch"
        :return: None
        """
        if self._branch_name is None:
            raise ValueError("No setting for branch-name")
        else:
            print "create branch and update package.json for the repos..."
            self.branch_existing_repositories()
            self.checkout_branch_repositories(self._branch_name)
            self.update_package_references(version=self._branch_name)
            commit_message = "update the dependencies version to {0}".format(self._branch_name)
            self.push_changed_repositories(commit_message)

    def branch_existing_repositories(self):
        """
        Issues create branch commands to repos in a provided manifest
        :return: None
        """
        if self._branch_name is None:
            print "Please provide the new branch name"
            sys.exit(2)

        repo_list = self._manifest.repositories
        if repo_list is None:
            print "No repository list found in manifest file"
            sys.exit(2)
        else:
            # Loop through list of repos and create specified branch on each
            for repo in repo_list:
                self.create_repo_branch(repo, self._branch_name)

    def create_repo_branch(self, repo, branch):
        """
        create branch  on the repos in the manifest file
        :param repo: A dictionary
        :return: None
        """
        try:
            repo_directory = self.directory_for_repo(repo)
            repo_url = repo["repository"]
            self.repo_operator.create_repo_branch(repo_url, repo_directory, branch)

        except RuntimeError as error:
            print "Exiting due to error: {0}".format(error)
            sys.exit(1)   
    
    def checkout_branch_repositories(self, branch):
        repo_list = self._manifest.repositories
        if repo_list is None:
            print "No repository list found in manifest file"
            sys.exit(2)
        else:
            # Loop through list of repos and checkout specified branch on each
            for repo in repo_list:
                self.checkout_repo_branch(repo, branch)

    def checkout_repo_branch(self, repo, branch):
        """
        checkout to a specify branch on repository
        :param repo: A dictionary
        :param branch: the specify branch name
        :return: None
        """
        try:
            repo_directory = self.directory_for_repo(repo)
            self.repo_operator.checkout_repo_branch(repo_directory, branch)
        except RuntimeError as error:
            print "Exiting due to error: {0}".format(error)
            sys.exit(1)

    def update_package_references(self, version=None):
        print "Update internal package lists"
        repo_list = self._manifest.repositories
        if repo_list is None:
            print "No repository list found in manifest file"
            sys.exit(2)
        else:
            # Loop through list of repos and update package.json on each
            for repo in repo_list:
                self.update_repo_package_list(repo, pkg_version=version)

    def update_repo_package_list(self, repo, pkg_version=None):
        """
        Update the package.json of repository to point to new version
        :param repo: a manifest repository entry
        :param pkg_version: the version of package.json to point to
        :return:
        """
        repo_dir = repo['directory-name']

        package_json_file = os.path.join(repo_dir, "package.json")
        if not os.path.exists(package_json_file):
            # if there's no package.json file, there is nothing more for us to do here
            return

        changes = False
        log = ""

        with open(package_json_file, "r") as fp:
            package_data = json.load(fp)
            if 'dependencies' in package_data:
                for package, version in package_data['dependencies'].items():
                    new_version = self._update_dependency(version, pkg_version=pkg_version)
                    if new_version != version:
                        log += "  {0}:\n    WAS {1}\n    NOW {2}\n".format(package,
                                                                           version,
                                                                           new_version)
                        package_data['dependencies'][package] = new_version
                        changes = True
        if changes:
            print "There are changes to dependencies for {0}\n{1}".format(package_json_file, log)
            os.remove(package_json_file)

            new_file = package_json_file
            with open(new_file, "w") as newfile:
                json.dump(package_data, newfile, indent=4, sort_keys=True)

        else:
            print "There are NO changes to data for {0}".format(package_json_file)


    def _update_dependency(self, version, pkg_version=None):
        """
        Check the specified package & version, and return a new package version if
        the package is listed in the manifest.

        :param version:
        :return:
        """
        if not version.startswith("git+"):
            return version

        url = strip_prefix(version, "git+")
        url = url.split('#')[0]
        new_url = url

        if pkg_version is None:
            for repo in self._manifest.repositories:
                if new_url == repo['repository']:
                    if 'directory-name' in repo:
                        new_url = os.path.abspath(repo['directory-name'])
                        return new_url
        else:
            new_url = "git+{url}#{pkg_version}".format(url=new_url, pkg_version=pkg_version)
            return new_url

        return version

    def push_changed_repositories(self, commit_message):
        repo_list = self._manifest.repositories
        if repo_list is None:
            print "No repository list found in manifest file"
            sys.exit(2)
        else:
            # Loop through list of repos and publish changes on each
            for repo in repo_list:
                self.push_changed_repo(repo, commit_message)

    def push_changed_repo(self, repo, commit_message):
        """
        publish changes in the repository
        :param repo: A dictionary
        :param commit_message: the message to be added to the commit
        :return: None
        """
        repo_dir = repo['directory-name']

        try:
            self.repo_operator.push_repo_changes(repo_dir, commit_message)
        except RuntimeError as error:
            print "Exiting due to error: {0}".format(error)
            sys.exit(1)

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
                        required=True,
                        help="Git credentials for CI services",
                        action="append")
    parser.add_argument("--branch-name",
                        help="branch name applied to repos",
                        action="store")
    parser.add_argument("--jobs",
                        default=1,
                        help="Number of parallel jobs to run",
                        type=int)
    parser.add_argument('action',
                        nargs="+")

    parsed_args = parser.parse_args(args)
    return parsed_args


def main():
    try:
        # Parse arguments
        args = parse_command_line(sys.argv[1:])
    
        # Create and initial an instance of ManifestActions
        manifest_actions = ManifestActions(args.manifest, args.builddir, force=args.force, git_credentials=args.git_credential, jobs=args.jobs, actions=args.action, branch_name=args.branch_name)

        manifest_actions.execute_actions()
    except Exception,e:
        print e
        sys.exit(1)

if __name__ == "__main__":
    main()
    sys.exit(0)
