#!/usr/bin/env python
# Copyright 2016, DELLEMC, Inc.

"""
This is a command line program that makes a rackhd release to bintray.
This program build debian packages for repositories 
which checked out based on the given manifest file.

Usage:
./on-tools/manifest-build-tools/HWIMO-BUILD on-tools/manifest-build-tools/application/make-debian-release.py \
--build-directory b/ \
--manifest-name rackhd-devel \
--manifest-repo build-manifests/ \
--git-credential https://github.com,GITHUB \
--jobs 8 \
--is-official-release true\
--parameter-file downstream-files \
--force \
--sudo-credential SUDO_CREDS

The required parameters:
build-directory: A directory where all the repositories are cloned to. 
manifest-name: The name of a manifest file. 
               All the repositories are cloned based on the manifest file.
manifest-repo: The directory of manifest repository
git-credential: Git URL and credential for CI services: <URL>,<Credentials>

The optional parameters:
is-official-release: Whether this release is official. The default value is False
parameter-file: The file with parameters. The file will be passed to downstream jobs.
force: Use destination directory, even if it exists.
sudo-credential: The environment variable name of sudo credentials.
                 For example: SUDO_CRED=username:password
jobs: Number of parallel jobs(build debian packages) to run.
      The number is related to the compute architecture, multi-core processors..
force:
"""

import argparse
import os
import sys
import json

try:
    from reprove import ManifestActions
    from update_rackhd_version import RackhdDebianControlUpdater
    from version_generator import VersionGenerator
    from DebianBuilder import DebianBuilder
    import common
except ImportError as import_err:
    print import_err
    sys.exit(1)

def parse_args(args):
    """
    Parse script arguments.
    :return: Parsed args for assignment
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--build-directory',
                        required=True,
                        help="Top level directory that stores all the cloned repositories.",
                        action='store')

    parser.add_argument('--manifest-file',
                        required=True,
                        help="The file path of manifest",
                        action='store')

    parser.add_argument('--parameter-file',
                        help="The jenkins parameter file that will used for succeeding Jenkins job",
                        action='store',
                        default="downstream_parameters")

    parser.add_argument('--git-credential',
                        required=True,
                        help="Git URL and credential for CI services: <URL>,<Credentials>",
                        action='append',
                        default=None)

    parser.add_argument('--sudo-credential',
                        help="username:password pair for sudo user",
                        action='store',
                        default=None)

    parser.add_argument('--jobs',
                        help="Number of build jobs to run in parallel",
                        default=-1,
                        type=int,
                        action="store")

    parser.add_argument('--is-official-release',
                        default="false",
                        help="Whether this release is official",
                        action="store")

    parser.add_argument('--force',
                        help="Overwrite a directory even if it exists",
                        action="store_true")

    parsed_args = parser.parse_args(args)
    parsed_args.is_official_release = common.str2bool(parsed_args.is_official_release)
    return parsed_args

def update_rackhd_control(top_level_dir, is_official_release):
    """
    Update the rackhd/debian/control with the version of on-xxx.deb under $top_level_dir.
    :param top_level_dir: Top level directory that stores all the
                          cloned repositories.
    :param is_official_release: If true, this release is official release
    :return: None
    """
    updater = RackhdDebianControlUpdater(top_level_dir, is_official_release)
    updater.update_RackHD_control()

def generate_version_file(repo_dir, is_official_release):
    """
    Generate the version file for rackhd repository
    :param repo_dir: The directory of rackhd repository
    :param is_official_release: If true, this release is official release
    :return: True if succeed to compute version and write it into version file.
             Otherwise, False.
    """
    try:
        version_generator = VersionGenerator(repo_dir)
        version = version_generator.generate_package_version(is_official_release)
        if version != None:
            params = {}
            params['PKG_VERSION'] = version
            repo_name = os.path.basename(repo_dir)
            version_file = "{0}.version".format(repo_name)
            version_path = os.path.join(repo_dir, version_file)
            common.write_parameters(version_path, params)
            return True
    except Exception, e:
        raise RuntimeError("Failed to generate version file for {0} \ndue to {1}".format(repo_dir, e))

def run_build_scripts(top_level_dir, repos, jobs=1, sudo_creds=None):
    """
    Go into the directory provided and run all the building scripts.
    :param top_level_dir: Top level directory that stores all the
                          cloned repositories.
    :param repos: A list of repositories to be build
    :param jobs: Number of parallel jobs(build debian packages) to run.
    :param sudo_creds: the environment variable name of sudo credentials.
                       for example: SUDO_CRED=username:password
    :return:
        exit on failures
        None on success.
    """
    try:
        builder = DebianBuilder(top_level_dir, repos, jobs=jobs, sudo_creds=sudo_creds)
        builder.blind_build_all()
        builder.print_summary_report()
        builder.print_detailed_report()
        result = builder.get_build_result()
        if result:
            print "Debian building is finished successfully."
        else:
            #builder.print_detailed_report()
            print "Error found during debian building. cannot continue."
            sys.exit(2)
    except Exception, e:
        sys.exit(1)

def get_build_repos(directory):
    """
    :param directory: Directory that stores all the cloned repositories.
    :return: a list which contains the name of repositories under the directory
    """
    repos = []
    for filename in os.listdir(directory):
        repos.append(filename)
    return repos

def checkout_repos(manifest, builddir, force, git_credential, jobs):
    try:
        manifest_actions = ManifestActions(manifest, builddir, force=force, git_credentials=git_credential, jobs=jobs, actions=["checkout", "packagerefs"])
        manifest_actions.execute_actions()
    except Exception, e:
        print "Failed to checkout repositories according to manifest file {0} \ndue to {1}. Exiting now...".format(manifest, e)
        sys.exit(1)

def build_debian_packages(build_directory, jobs, is_official_release, sudo_creds):
    """
    Build debian packages
    """
    try:
        repos = get_build_repos(build_directory)
        for repo in repos:
            repo_dir = os.path.join(build_directory, repo)
            generate_version_file(repo_dir, is_official_release)

        # Build Debian packages of repositories except RackHD
        repos.remove("RackHD")
        # Run HWIMO-BUILD script under each repository to build debian packages
        run_build_scripts(build_directory, repos, jobs=jobs, sudo_creds=sudo_creds)

        # If on-xxx.deb build successfully, build Debian packages of RackHD
        repos = ["RackHD"]
        # Update the debian/control of rackhd to depends on specified version of component of raqkhd
        update_rackhd_control(build_directory, is_official_release)
        # Run HWIMO-BUILD script under each repository to build debian packages
        run_build_scripts(build_directory, repos, sudo_creds=sudo_creds)

    except Exception, e:
        print "Failed to build debian packages under {0} \ndue to {1}, Exiting now".format(build_directory, e)
        sys.exit(1)

def write_downstream_parameter_file(build_directory, is_official_release, parameter_file):
    try:
        params = {}

        # Add rackhd version to downstream parameters
        rackhd_repo_dir = os.path.join(build_directory, "RackHD")
        version_generator = VersionGenerator(rackhd_repo_dir)
        rackhd_version = version_generator.generate_package_version(is_official_release)
        if rackhd_version != None:
            params['RACKHD_VERSION'] = rackhd_version
        else:
            raise RuntimeError("Version of {0} is None. Maybe the repository doesn't contain debian directory ".format(rackhd_repo_dir))

        # Write downstream parameters to downstream parameter file.
        common.write_parameters(parameter_file, params)
    except Exception, e:
        raise RuntimeError("Failed to generate version file for {0} \ndue to {1}".format(repo_dir, e))

def main():
    """
    Build all the debians.
    Exit on encountering any error.
    """
    args = parse_args(sys.argv[1:])
    checkout_repos(args.manifest_file, args.build_directory, args.force, args.git_credential, args.jobs)
    build_debian_packages(args.build_directory, args.jobs, args.is_official_release, args.sudo_credential)
    write_downstream_parameter_file(args.build_directory, args.is_official_release, args.parameter_file)

if __name__ == '__main__':
    main()
