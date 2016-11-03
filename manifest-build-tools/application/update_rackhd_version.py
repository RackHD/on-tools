#!/usr/bin/env python

"""
usage:
./manifest-build-tools/HWIMO-BUILD manifest-build-tools/application/update_rackhd_version.py \
--manifest-repo-url https://github.com/PengTian0/build-manifests \
--manifest-name rackhd-devel \
--builddir b \
--git-credential https://github.com/PengTian0,GITHUB \
--force

The parameters to this script:
manifest-repo-url: the url of manifest repository
manifest-repo-commit: the commit of repository manifest
manifest-name: the filename of manifest
builddir: the destination for checked out repositories
version-file: the version file used to save the version of rackhd
force: use destination directory, even if it exists
git-credential: url, credentials pair for the access to github repos
is-official-release: if true, this release is official, the default value is false
                     
The required parameters:
manifest-repo-url
manifest-name
builddir
git-credential
"""
import argparse
import sys
import os
import shutil
from RepositoryOperator import RepoOperator
from reprove import ManifestActions
from version_generator import VersionGenerator
from common import *

import deb822
import subprocess

class UpdateRackhdVersion(object):
    def __init__(self, manifest_url, manifest_commit, manifest_name, builddir):
        """
        __force - Overwrite a directory if it exists
        __git_credential - url, credentials pair for the access to github repos
        __manifest_url - The url of Repository manifest
        __manifest_commit - The commit of Repository manifest
        __manifest_name - The file name of manifest
        __builddir - Destination for checked out repositories
        __is_official_release - True if the official is official release
        :return:
        """
        self._force = False
        self._git_credentials = None
        self._manifest_url = manifest_url
        self._manifest_commit = manifest_commit
        self._manifest_name = manifest_name
        self._builddir = builddir
        
        self._is_official_release = False
        
        self._manifest_path = None
        self._manifest_builddir = None
        self._manifest_repo_dir = None
        self.manifest_actions = None

        self.repo_operator = RepoOperator()
        
        
    def set_git_credentials(self, git_credential):
        """
        Standard setter for git_credentials
        :return: None
        """
        self._git_credentials = git_credential
        self.repo_operator.setup_gitbit(credentials=self._git_credentials)

    def set_force(self, force):
        """
        Standard setter for force
        :return: None
        """
        self._force = force

    def set_is_official_release(self, is_official_release):
        """
        Standard setter for is_official_release
        :return: None
        """
        self._is_official_release = is_official_release

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

    def clone_manifest(self):
        """
        clone manifest to build dir
        :return: None
        """
        try:
            if self._manifest_url and self._manifest_commit:
                manifest_repo_dir = self.repo_operator.clone_repo(self._manifest_url, self._builddir, repo_commit=self._manifest_commit)
                self._manifest_repo_dir =  manifest_repo_dir
                self._initial_manifest_actions()

            else:
                print "manifest url or manifest commit can not be null"
                sys.exit(1)
        except Exception,e:
            print "Failed to clone manifest due to {0}. \n Exiting now...".format(e)
            sys.exit(1)


    def _initial_manifest_actions(self):
        """
        initial an instance of Manifest_Actions
        the instance is used to clone repositories in manifest file
        :return: None
        """
        self._manifest_path = os.path.join(self._manifest_repo_dir, self._manifest_name)
        self._manifest_builddir = os.path.join(self._builddir, self._builddir)
        self.manifest_actions = ManifestActions(self._manifest_path, self._manifest_builddir)
        if self._git_credentials:
            self.manifest_actions.set_git_credentials(self._git_credentials)
        self.manifest_actions.set_jobs(8)

        self.manifest_actions.check_builddir()
        self.manifest_actions.get_repositories()


    def _get_repo_dir(self, repo_name):
        """
        find the repository directory in build dir
        :param: the name of repo
        :return: directory of repo
        """
        repo_list = self.manifest_actions.get_manifest().get_repositories()
        repo_dir = ""
        for repo in repo_list:
            if 'repository' in repo:
                repo_url = repo['repository']
                repo_name = strip_suffix(os.path.basename(repo_url), ".git")
                if repo_name == repo_name:
                    if 'directory-name' in repo:
                        repo_dir = repo['directory-name']
                    else:
                        repo_dir = self.manifest_actions.directory_for_repo(repo)

        if len(repo_dir) > 0:
            return repo_dir
        else:
            raise RuntimeError("Failed to find repository {0} at {1}".format(repo_name, self._manifest_builddir))


    def generate_RackHD_version(self):
        """
        generate the version of RackHD
        :return: a big version like 1.1.1 if the release if official release
                 a complete version like 1.1.1~rc-20161009123456-abcd123 if the release if daily build
        """
        try:
            rackhd_dir = self._get_repo_dir("RackHD")
            version_generator = VersionGenerator(rackhd_dir, self._manifest_repo_dir)
            version = version_generator.generate_package_version(self._is_official_release)
            return version
        except Exception,e:
            print "Failed to generate RackHD version due to {0} \n Exiting now...".format(e)
            sys.exit(1) 


    def _get_control_depends(self, control_path):
        """
        Parse debian control file
        :param control_path: the path of control file
        :return: a dictionay which contains all the package in field Depends
        """
        if not os.path.isfile(control_path):
            raise RuntimeError("Can't parse {0} because it is not a file".format(control))

        for paragraph in deb822.Deb822.iter_paragraphs(open(control_path)):
            for item in paragraph.items():
                if item[0] == 'Depends':
                    packages = item[1].split("\n")
                    return packages
        return None

    def _update_dependency(self, debian_dir, version_dict):
        """
        update the dependency version of RackHD/debian/control
        :param: debian_dir: the directory of RackHD/debian
        :param: version_dict: a dictionay which includes the version of on-xxx
        :return: None
        """
        control = os.path.join(debian_dir, "control")
        
        if not os.path.isfile(control):
            raise RuntimeError("Can't update dependency of {0} because it is not a file".format(control))

        new_control = os.path.join(debian_dir, "control_new")
        new_control_fp = open(new_control , "wb")

        packages = self._get_control_depends(control)

        with open(control) as fp:
            package_count = 0
            is_depends = False
            for line in fp:
                if line.startswith('Depends'):
                    package_count += 1
                    is_depends = True
                    new_control_fp.write("Depends: ")
                    # Start to write the dependes
                    # If the depends is on-xxx, it will be replace with on-xxx (= 1.1...)
                    for package in packages:
                        package_name = package.split(',',)[0].strip()
                        if ' ' in package_name:
                            package_name = package_name.split(' ')[0]
                        if package_name in version_dict:
                            if ',' in package:
                                depends_str = "         {0} (= {1}),{2}".format(package_name, version_dict[package_name], os.linesep)
                            else:
                                depends_str = "         {0} (= {1}){2}".format(package_name, version_dict[package_name], os.linesep)
                            new_control_fp.write(depends_str)
                        else:
                            new_control_fp.write("{0}{1}".format(package, os.linesep))
                else:
                    if not is_depends or package_count >= len(packages):
                        new_control_fp.write(line)
                    else:
                        package_count += 1

        new_control_fp.close()
        os.remove(control)
        os.rename(new_control, control)

    def _generate_version_dict(self):
        """
        generate a dictory which includes the version of package on-xxx
        :return: a dictory
        """
        repo_list = self.manifest_actions.get_manifest().get_repositories()
        version_dict = {}
        for repo in repo_list:
            if 'directory-name' in repo:
                repo_dir = repo['directory-name']
            else:
                repo_dir = self.manifest_actions.directory_for_repo(repo)

            version_generator = VersionGenerator(repo_dir, self._manifest_repo_dir)
            version = version_generator.generate_package_version(self._is_official_release)
            if version != None:
                if 'repository' in repo:
                    repo_url = repo['repository']
                    repo_name = strip_suffix(os.path.basename(repo_url), ".git")
                    version_dict[repo_name] = version

        return version_dict

    def update_RackHD_control(self):
        """
        udpate RackHD/debian/control according to manifest
        :return: None     
        """
        try:
            rackhd_dir = self._get_repo_dir("RackHD")
            debian_dir = os.path.join(rackhd_dir, "debian")
            version_dict = self._generate_version_dict()
            self._update_dependency(debian_dir, version_dict)
        except Exception, e:
            print "Failed to update RackHD/debian/control due to {0}".format(e)
            sys.exit(1)

        
def parse_command_line(args):
    """
    Parse script arguments.
    :return: Parsed args for assignment
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-repo-url",
                        required=True,
                        help="the url of repository manifest",
                        action="store")
    
    parser.add_argument("--manifest-repo-commit",
                        default="HEAD",
                        help="the commit of repository manifest",
                        action="store")

    parser.add_argument("--manifest-name",
                        required=True,
                        help="repository manifest file",
                        action="store")

    parser.add_argument("--builddir",
                        required=True,
                        help="destination for checked out repositories",
                        action="store")

    parser.add_argument('--version-file',
                        help="The file that is used to save rackhd version",
                        action='store',
                        default="release_version")

    parser.add_argument("--force",
                        help="use destination dir, even if it exists",
                        action="store_true")

    parser.add_argument("--git-credential",
                        required=True,
                        help="Git credentials for CI services",
                        action="append")

    parser.add_argument("--is-official-release",
                        default=False,
                        help="whether this release is official",
                        action="store_true")

    parsed_args = parser.parse_args(args)
    return parsed_args


def write_downstream_parameters(filename, params):
    """
    Add/append downstream parameter (java variable value pair) to the given
    parameter file. If the file does not exist, then create the file.

    :param filename: The parameter file that will be used for making environment
     variable for downstream job.
    :param params: the parameters dictionary
    :return:
            None on success
            Raise any error if there is any
    """
    if filename is None:
        return

    with open(filename, 'w') as fp:
        try:
            for key in params:
                entry = "{key}={value}\n".format(key=key, value=params[key])
                fp.write(entry)
        except IOError:
            print "Unable to write parameter(s) for next step(s), exit"
            exit(2)

def main():
    # Parse arguments
    args = parse_command_line(sys.argv[1:])

    # Start to initial an instance of UpdateRackhdVersion
    updater = UpdateRackhdVersion(args.manifest_repo_url, args.manifest_repo_commit, args.manifest_name, args.builddir)
    if args.force:
        updater.set_force(args.force)
        updater.check_builddir()

    if args.is_official_release:
        updater.set_is_official_release(args.is_official_release)

    if args.git_credential:
        updater.set_git_credentials(args.git_credential)

    # Update the RackHD/debian/control according to manifest
    updater.check_builddir()
    updater.clone_manifest()
    RackHD_version = updater.generate_RackHD_version()
    updater.update_RackHD_control()

    if os.path.isfile(args.version_file):  # Delete existing version file
        os.remove(args.version_file)

    # Write parameters to version file
    downstream_parameters = {}
    downstream_parameters['PKG_VERSION'] = RackHD_version
    write_downstream_parameters(args.version_file, downstream_parameters)

if __name__ == "__main__":
    main()
    sys.exit(0)
