#!/usr/bin/env python
# Copyright 2016, DELLEMC, Inc.

"""
usage:
./on-tools/manifest-build-tools/HWIMO-BUILD on-tools/manifest-build-tools/application/update_dependencies.py \
--manifest rackhd-devel \
--builddir b \
--force \
--git-credential https://github.com/PengTian0,GITHUB \
--jobs 8 \
--is-official-release true/false
                     
The required parameters:
manifest: The file path of manifest.
builddir: The destination for repositories in manifest stored.
          Repositories under the directory include on-xxx and RackHD
git-credential: url, credentials pair for the access to github repos
The optional parameter:
force: Overwrite the build directory if it exists.
is-official-release: if true, this release is official, the default value is false
jobs: number of parallel jobs to run(checkout repositories). The number is related to the compute architecture, multi-core processors...
"""
import argparse
import sys
import os
import deb822

try:
    from reprove import ManifestActions
    from version_generator import VersionGenerator
    import common
except ImportError as import_err:
    print import_err
    sys.exit(1)

class RackhdDebianControlUpdater(object):
    def __init__(self, builddir, is_official_release=False):
        """
        Compute the version of each repository under builddir
        and update the debian/control with these versions
        __manifest_repo_dir - The directory of Repository manifest
        __builddir - Destination for checked out repositories
        __is_official_release - True if the official is official release
        :return: None
        """
        self._builddir = builddir
        self._is_official_release = is_official_release

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
        version_dict = {}
        for repo in os.listdir(self._builddir):
            repo_dir = os.path.join(self._builddir, repo)
            version_generator = VersionGenerator(repo_dir)
            version = version_generator.generate_package_version(self._is_official_release)
            if version != None:
                version_dict[repo] = version

        return version_dict

    def update_RackHD_control(self):
        """
        udpate RackHD/debian/control according to manifest
        :return: None     
        """
        try:
            rackhd_dir = os.path.join(self._builddir, "RackHD")
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
    parser.add_argument("--manifest",
                        required=True,
                        help="the path of manifest file",
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

    parser.add_argument('--jobs',
                        help="Number of build jobs to run in parallel",
                        default=-1,
                        type=int,
                        action="store")

    parser.add_argument('--is-official-release',
                        default="false",
                        help="Whether this release is official",
                        action="store")

    parsed_args = parser.parse_args(args)
    parsed_args.is_official_release = common.str2bool(parsed_args.is_official_release)

    return parsed_args

def checkout_repos(manifest, builddir, force, git_credential, jobs):
    manifest_actions = ManifestActions(manifest, builddir, force=force, git_credentials=git_credential, jobs=jobs, actions=["checkout"])
    manifest_actions.execute_actions()

def main():
    # Parse arguments
    args = parse_command_line(sys.argv[1:])

    # Checkout repositories according to manifest file
    checkout_repos(args.manifest, args.builddir, args.force, args.git_credential, args.jobs)

    # Start to initial an instance of UpdateRackhdVersion
    updater = RackhdDebianControlUpdater(args.builddir, is_official_release=args.is_official_release)

    # Update the RackHD/debian/control according to manifest
    updater.update_RackHD_control()


if __name__ == "__main__":
    main()
    sys.exit(0)
