#!/usr/bin/env python
# Copyright 2015-2016, EMC, Inc.

"""
The script generate a new manifest for a new branch according to another manifest

usage:
./on-tools/manifest-build-tools/HWIMO-BUILD on-tools/manifest-build-tools/application/manifest_generator.py \
--source-manifest build-manifest/rackhd-devel \
--dest-manifest build-manifest/rackhd-release-1.2.5 \
--branch branch/release-1.2.5 \
--force \
--publish \
--publish-branch master \
--git-credential https://github.com,GITHUB \
--builddir b \
--jobs 8

The required parameters: 
source-manifest: The path of manifest. The new manifest is generated according to it.
dest-manifest: The path of the new manifest
branch: The new branch name
git-credential: Git credentials for CI services.
builddir: The directory for checked repositories.

The optional parameters:
force: If true, overwrite the destination manifest file even it already exists.
publish: If true, the script will try to run "git push" under the directory of dest manifest. 
publish-branch: The new manifest will be pushed to the branch.
jobs: number of parallel jobs to run(when check out code). The number is related to the compute architecture, multi-core processors...
"""
import os
import sys
import argparse
import subprocess
import json
import traceback
import shutil

from RepositoryOperator import RepoOperator
from manifest import Manifest
from common import *

class ManifestGenerator(object):
    def __init__(self, source, dest, branch, builddir, git_credentials, force=False, jobs=1):
        """
        Generate a new manifest for new branch according to a source manifest file.

        _source_manifest_file: the path of source manifest
        _dest_manifest_file: the path of new manifest
        _new_branch: the new branch name
        _force: overwrite the destination if it exists.
        _git_credentials: url, credentials pair for the access to github repos.
        _builddir: the destination for checked out repositories.
        _jobs: number of parallel jobs to run. The number is related to the compute architecture, multi-core processors...
        :return: None
        """
        self._source_manifest_file = source
        self._dest_manifest_file = dest
        self._new_branch = branch
        self._git_credentials = git_credentials
        self._manifest = None
        self._force = force
        self._builddir = builddir
        self._jobs = jobs
        self.initiate_manifest()
        self.repo_operator = RepoOperator(git_credentials)
        self.check_builddir()

    def set_force(self, force):
        """
        Standard setter for force
        :param force: if true, overwrite a directory file if it exists
        :return: None
        """
        self._force = force

    def initiate_manifest(self):
        """
        initial manifest and validate it
        :return: None
        """
        self._manifest = Manifest(self._source_manifest_file)
        self._manifest.validate_manifest()

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

    def update_repositories_with_lastest_commit(self, repositories):
        """
        update the commit-id of repository with the lastest commit id
        :param repositories: a list of repository directory
        :return: None
        """
        self.repo_operator.clone_repo_list(repositories, self._builddir, jobs=self._jobs)
        for repo in repositories:
            repo_dir = self.directory_for_repo(repo)
            repo["commit-id"] = self.repo_operator.get_lastest_commit_id(repo_dir)

    def update_manifest(self):
        """
        update the manifest with new branch
        :return: None
        """
        repositories = self._manifest.repositories
        downstream_jobs = self._manifest.downstream_jobs
        build_name = os.path.basename(self._dest_manifest_file)

        for repo in repositories:
            repo["branch"] = self._new_branch
            repo["commit-id"] = ""
        self.update_repositories_with_lastest_commit(repositories)

        for job in downstream_jobs:
            job["branch"] = self._new_branch
            repo["commit-id"] = ""
        self.update_repositories_with_lastest_commit(downstream_jobs)
        
        self._manifest.build_name = build_name
        self._manifest.validate_manifest()
        
    def generate_manifest(self):
        """
        generate a new manifest
        :return: None
        """
        dest_dir = os.path.dirname(self._dest_manifest_file)
        dest_file = os.path.basename(self._dest_manifest_file)
        for filename in os.listdir(dest_dir):
            if filename == dest_file and self._force == False:
                raise RuntimeError("The file {0} already exist under {1}. \n \
                                    If you want to overrite the file, please specify --force."
                                    .format(dest_file, dest_dir))

        with open(self._dest_manifest_file, 'w') as fp:
            json.dump(self._manifest.manifest, fp, indent=4, sort_keys=True)

def parse_command_line(args):
    """
    Parse script arguments.
    :return: Parsed args for assignment
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest",
                        required=True,
                        help="the file path of source manifest",
                        action="store")
    parser.add_argument("--dest-manifest",
                        required=True,
                        help="the destination file path of manifest",
                        action="store")
    parser.add_argument("--branch",
                        required=True,
                        help="The branch of repositories in new manifest",
                        action="store")
    parser.add_argument("--force",
                        help="use destination manifest file, even if it exists",
                        action="store_true")
    parser.add_argument("--builddir",
                        required=True,
                        help="destination for checked out repositories",
                        action="store")

    parser.add_argument("--publish",
                        help="Push the new manifest to github",
                        action='store_true')
    parser.add_argument("--publish-branch",
                        help="Push the new manifest to branch",
                        action='store')
    parser.add_argument("--git-credentials",
                        help="Git credentials for CI services",
                        action="append")
    parser.add_argument("--jobs",
                        default=1,
                        help="Number of parallel jobs to run",
                        type=int)

    parsed_args = parser.parse_args(args)
    return parsed_args

def main():
    # parse arguments
    args = parse_command_line(sys.argv[1:])
    generator = ManifestGenerator(args.source_manifest, args.dest_manifest, args.branch, args.builddir, args.git_credentials, jobs=args.jobs, force=args.force)
    try:
        generator.update_manifest()
        if args.force:
            generator.set_force(args.force)
        
        if args.publish:
            if args.git_credentials and args.publish_branch:
                repo_operator = RepoOperator(args.git_credentials)
                commit_message = "add a manifest file for new branch {0}".format(args.branch)
                repo_dir = os.path.dirname(args.dest_manifest)
                repo_operator.checkout_repo_branch(repo_dir, args.publish_branch)
                generator.generate_manifest()
                repo_operator.push_repo_changes(repo_dir, commit_message, push_all=True)
            else:
                print "Please specify the git-credential and publish-branch if you want to push the new manifest"
                sys.exit(1)
        else:
            generator.generate_manifest()
    except Exception, e:
        traceback.print_exc()
        print "Failed to generate new manifest for {0} due to \n{1}\nExiting now".format(args.branch, e)
        sys.exit(1)

if __name__ == "__main__":
    main()
    sys.exit(0)
