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
--git-credential https://github.com,GITHUB

The required parameters: 
source-manifest: The path of manifest. The new manifest is generated according to it.
dest-manifest: The path of the new manifest
branch: The new branch name

The optional parameters:
force: If true, overwrite the destination manifest file even it already exists.
publish: If true, the script will try to push the new manifest to github. That means the dest manifest should         under the manifest repository.
publish-branch: The new manifest will be pushed to the branch.
git-credential: Git credentials for CI services.
                If publish is true, the parameter is required.
"""
import os
import sys
import argparse
import subprocess
import json
import traceback

from RepositoryOperator import RepoOperator
from manifest import Manifest

class ManifestGenerator(object):
    def __init__(self, source, dest, branch):
        """
        Generate a new manifest for new branch according to a source manifest file.

        __source_manifest_file: the path of source manifest
        __dest_manifest_file: the path of new manifest
        __new_branch: the new branch name
        __force: overwrite the destination manifest file if it exists.
        :return: None
        """
        self._source_manifest_file = source
        self._dest_manifest_file = dest
        self._new_branch = branch
        self._manifest = None
        self._force = False
        self.initiate_manifest()

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

    def update_manifest(self):
        """
        update the manifest with new branch
        :return: None
        """
        repositories = self._manifest.get_repositories()
        downstream_jobs = self._manifest.get_downstream_jobs()
        build_name = os.path.basename(self._dest_manifest_file)

        for repo in repositories:
            repo["branch"] = self._new_branch

        for job in downstream_jobs:
            job["branch"] = self._new_branch

        self._manifest.set_build_name(build_name)

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
            json.dump(self._manifest.get_manifest(), fp, indent=4, sort_keys=True)

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

    parser.add_argument("--publish",
                        help="Push the new manifest to github",
                        action='store_true')
    parser.add_argument("--publish-branch",
                        help="Push the new manifest to branch",
                        action='store')
    parser.add_argument("--git-credential",
                        help="Git credentials for CI services",
                        action="append")

    parsed_args = parser.parse_args(args)
    return parsed_args

def main():
    # parse arguments
    args = parse_command_line(sys.argv[1:])
    generator = ManifestGenerator(args.source_manifest, args.dest_manifest, args.branch)
    try:
        generator.update_manifest()
        if args.force:
            generator.set_force(args.force)
        
        if args.publish:
            if args.git_credential and args.publish_branch:
                repo_operator = RepoOperator(args.git_credential)
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
