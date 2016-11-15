#!/usr/bin/env python
# Copyright 2015-2016, EMC, Inc.

"""
The script compute the version of a package, just like:
1.1-1-devel-20160809150908-7396d91

usage:
./on-tools/manifest-build-tools/HWIMO-BUILD on-tools/manifest-build-tools/application/version_generator.py 
--repo-dir /home/onrack/rackhd/release/rackhd-repos/PengTian0/b/b/on-http
--manifest-repo-dir /home/onrack/rackhd/release/rackhd-repos/PengTian0/b/build-manifests
--is-official-release

Because this script need to import scripts under lib.
The script HWIMO-BUILD helps to add the scripts under lib to python path.

The required parameters: 
repo-dir
manifest-repo-dir

The optional parameters:
is-official-release (default value is false)
"""
import os
import sys
import argparse
import datetime
import subprocess
from RepositoryOperator import RepoOperator
from common import *

class VersionGenerator(object):
    def __init__(self, repo_dir, manifest_repo_dir):
        """
        This module compute the version of a repository
        The version for candidate release: {big-version}~{version-stage}-{small-version}
        The big version is parsed from debian/changelog
        The version-stage is devel if branch is master; or rc if branch if not master
        The samll version is consist of the commit hash and commit date of manifest repository
        :return:None
        """
        self._repo_dir = repo_dir
        self._manifest_repo_dir = manifest_repo_dir
        self.repo_operator = RepoOperator()
 
    def generate_small_version(self):
        """
        Generate the small version which consists of commit date and commit hash of manifest repository
        According to small version, users can track the commit of all repositories in manifest file
        return: small version 
        """

        ts_str = self.repo_operator.get_lastest_commit_date(self._manifest_repo_dir)
        date = datetime.datetime.utcfromtimestamp(int(ts_str)).strftime('%Y%m%d%H%M%SZ')
        commit_id = self.repo_operator.get_lastest_commit_id(self._manifest_repo_dir)
        version = "{date}-{commit}".format(date=date, commit=commit_id[0:7])
        return version

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

    def generate_big_version(self):
        """
        Generate the big version according to changelog
        The big version is the latest version of debian/changelog
        return: big version
        """
        repo_url = self.repo_operator.get_repo_url(self._repo_dir)
        repo_name = strip_suffix(os.path.basename(repo_url), ".git")
        # If the repository has the debianstatic/repository name/,
        # create a soft link to debian before compute version
        debian_exist = self.debian_exist()
        linked = False
        if not debian_exist:
            for filename in os.listdir(self._repo_dir):
                if filename == "debianstatic":
                    debianstatic_dir = os.path.join(self._repo_dir, "debianstatic")
                    for debianstatic_filename in os.listdir(debianstatic_dir):
                        if debianstatic_filename == repo_name:
                            debianstatic_repo_dir = "debianstatic/{0}".format(repo_name)
                            link_dir(debianstatic_repo_dir, "debian", self._repo_dir)
                            linked = True
        if not debian_exist and not linked:
            return None
        cmd_args = ["dpkg-parsechangelog", "--show-field", "Version"]
        proc = subprocess.Popen(cmd_args,
                                cwd=self._repo_dir,
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                shell=False)
        (out, err) = proc.communicate()

        if linked:
            os.remove(os.path.join(self._repo_dir, "debian"))

        if proc.returncode == 0:
            return out.strip()
        else:
            raise RuntimeError("Failed to parse version in debian/changelog due to {0}".format(err))
        
    def generate_version_stage(self):
        """
        Generate the version stage according to the stage of deveplopment
        return: devel ,if the branch is master
                rc, if the branch is not master
        """
        current_branch = self.repo_operator.get_current_branch(self._repo_dir)
        version_stage = ""
        if "master" in current_branch:
            version_stage = "devel"
        else:
            version_stage = "rc"
        return version_stage
        
    def generate_package_version(self, is_official_release):
        """
        generate the version of package, just like:
        1.1-1-devel-20160809150908-7396d91 or 1.1-1
        :return: package version
        """
        big_version = self.generate_big_version()
        if big_version is None:
            logging.warning("Failed to generate big version, maybe the {0} doesn't contain debian directory".format(self._repo_dir))
            return None

        if is_official_release:
            version = big_version
        else:
            version_stage = self.generate_version_stage()
            small_version = self.generate_small_version()

            if version_stage is None or small_version is None:
                raise RuntimeError("Failed to generate version for {0}, due to the candidate version or small version is None".format(self._repo_dir))

            version = "{0}~{1}-{2}".format(big_version, version_stage, small_version)
        
        return version

def parse_command_line(args):
    """
    Parse script arguments.
    :return: Parsed args for assignment
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-dir",
                        required=True,
                        help="the directory of repository",
                        action="store")
    parser.add_argument("--manifest-repo-dir",
                        required=True,
                        help="the directory of manifest repository",
                        action="store")

    parser.add_argument("--is-official-release",
                        default=False,
                        help="This release if official",
                        action="store_true")

    parsed_args = parser.parse_args(args)
    return parsed_args

def main():
    # parse arguments
    args = parse_command_line(sys.argv[1:])
    generator = VersionGenerator(args.repo_dir, args.manifest_repo_dir)
    try:
        version = generator.generate_package_version(args.is_official_release)
        print version
    except Exception, e:
        logging.error("Failed to generate version for {0} due to {1}\n Exiting now".format(args.repo_dir, e))
        sys.exit(1)

if __name__ == "__main__":
    main()
    sys.exit(0)
