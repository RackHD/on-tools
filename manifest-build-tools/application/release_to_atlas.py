#!/usr/bin/env python
# Copyright 2016, EMC, Inc.

"""
This is a command line program that upload vagrant.boxs to atlas.

usage:
    ./on-tools/manifest-build-tools/HWIMO-BUILD \
    on-tools/manifest-build-tools/application/release_to_atlas.py \
    --build-directory b/RackHD/packer \
    --atlas-url https://atlas.hashicorp.com/api/v1 \
    --atlas-username rackhd \
    --atlas-name rackhd \
    --atlas-token ****** \
    --atlas-version 1.2.3 \
    --is-release true

The required parameters:
    build-directory: A directory where box files laid in.
    atlas-token: atlas access token.

The optional parameters:
    provider: The provider of vagrant box, virtualbox, vmware_fusion .etc, default: virtualbox
    atlas-url: Base URL for Atlas, default: https://atlas.hashicorp.com/api/v1
    atlas-username: The account name of atlas, default: rackhd
    atlas-name: The box name under a specific account of atlas, default: rackhd
    atlas-version: The box version in atlas, default: version number when is_release
                   0.month.day when is ci_builds.
"""

import sys
import argparse
import requests
import subprocess

try:
    import common
except ImportError as import_err:
    print import_err
    sys.exit(1)

class Atlas(object):
    """
    A simple class of atlas.
    An instance of 'class Atlas' represents a box in Atlas.
        default: rackhd/rackhd in official Atlas server.
    """
    def __init__(self, atlas_url, atlas_username, atlas_name, atlas_token):
        self.atlas_url = atlas_url or "https://atlas.hashicorp.com/api/v1"

        self.atlas_username = atlas_username or "rackhd"
        self.atlas_name = atlas_name or "rackhd"
        self.box = "/".join(["box", self.atlas_username, self.atlas_name])

        self.atlas_token = atlas_token

        self.session = requests.Session()
        self.session.headers.update({'X-Atlas-Token': self.atlas_token})

    def upload_handler(self, atlas_version, provider, box_file):
        """
        Upload a box file to atlas.
        See https://vagrantcloud.com/help/vagrant/boxes/create for more details
        """
        if not self.version_exist(atlas_version):
            self.create_version(atlas_version)

        if not self.provider_exist(atlas_version, provider):
            self.create_provider(atlas_version, provider)

        self.upload_box(atlas_version, provider, box_file)

    def create_version(self, atlas_version):
        """
        Create box version
        """
        create_version_url = self.generate_url("create_version")
        version_data = {'version[version]': atlas_version}
        print create_version_url
        resp = self.session.post(create_version_url, data=version_data)
        if resp.ok:
            print "Create box version {0} successfully.".format(atlas_version)
        else:
            print "Failed to create box version.\n {0}".format(resp.text)
            sys.exit(1)

    def create_provider(self, atlas_version, provider):
        """
        Create box provider of a specific version
        """
        create_provider_url = self.generate_url("create_provider", atlas_version)
        provider_data = {'provider[name]': provider}
        resp = self.session.post(create_provider_url, data=provider_data)
        if resp.ok:
            print "Create box provider {0} of version {1} successfully.".format(provider, atlas_version)
        else:
            print "Failed to create box provider.\n {0}".format(resp.text)
            sys.exit(1)

    def upload_box(self, atlas_version, provider, box_file):
        """
        Upload one box to a specific version/provider
        """
        upload_box_url = self.generate_url("upload_box", atlas_version, provider)
        resp = self.session.get(upload_box_url)
        if resp.ok:
            upload_path = resp.json()["upload_path"]
            cmd = "curl -X PUT --upload-file " +  box_file  + " " +  upload_path
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            retval = p.wait()
            if retval == 0 :
                print "Upload box {0} to version/{1}/provider/{2} successfully!".format(box_file, atlas_version, provider)
            else:
                print "Failed to Upload box {0} to version/{1}/provider/{2}!\n {3}".format(box_file, atlas_version, provider,retval)
                sys.exit(1)

    def version_exist(self, atlas_version):
        """
        Check if box version exists
        """
        check_version_url = self.generate_url("check_version", atlas_version)
        resp = self.session.get(check_version_url)
        if resp.ok:
            print "Box version {0} already exists.".format(atlas_version)
            return True
        print "Box version {0} doesn't' exist, will be created soon.".format(atlas_version)
        return False

    def provider_exist(self, atlas_version, provider):
        """
        Check if box provider exists.
        NOTICE: provider depends on a specific box version.
        """
        if not self.version_exist(atlas_version):
            print "Box version {0} doesn't' exist, please create version before check provider.".format(atlas_version)
            return False
        check_provider_url = self.generate_url("check_provider", atlas_version, provider)
        resp = self.session.get(check_provider_url)
        if resp.ok:
            print "{0} provider of version {1} already exists!".format(provider, atlas_version)
            return True
        print "{0} provider of version {1} doesn't' exist, will be created soon".format(provider, atlas_version)
        return False

    def generate_url(self, purpose, atlas_version=None, provider=None):
        """
        Tool method, Generate all possible urls according to purpose
        """
        purpose_handler = {
            "check_version": lambda atlas_version, provider: "/".join([self.atlas_url, self.box, "version/{0}".format(atlas_version)]),
            "create_version": lambda atlas_version, provider: "/".join([self.atlas_url, self.box, "versions"]),
            "check_provider": lambda atlas_version, provider: "/".join([self.atlas_url, self.box, "version/{0}/provider/{1}".format(atlas_version, provider)]),
            "create_provider": lambda atlas_version, provider: "/".join([self.atlas_url, self.box, "version/{0}/providers".format(atlas_version)]),
            "upload_box": lambda atlas_version, provider: "/".join([self.atlas_url, self.box, "version/{0}/provider/{1}".format(atlas_version, provider), "upload"])
        }
        return purpose_handler[purpose](atlas_version, provider)

def parse_args(args):
    """
    Parse script arguments.
    :return: Parsed args for assignment
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('--build-directory',
                        required=True,
                        help="A directory where box files laid in",
                        action='store')

    parser.add_argument('--atlas-url',
                        help="Base URL for Atlas, default: https://atlas.hashicorp.com/api/v1",
                        action='store')

    parser.add_argument('--atlas-username',
                        help="The account name of atlas, default: rackhd",
                        action='store')

    parser.add_argument('--atlas-name',
                        help="The repo name under a specific account of atlas, default: rackhd",
                        action='store')

    parser.add_argument('--atlas-token',
                        help="atlas access token",
                        action='store')

    parser.add_argument('--atlas-version',
                        help="atlas access token",
                        action='store')

    parser.add_argument('--is-release',
                        help="if this is a step of rlease build",
                        default=False,
                        action='store')

    parsed_args = parser.parse_args(args)
    return parsed_args

def upload_boxs(build_directory, atlas, is_release, atlas_version):
    """
    The function will walk through all sub-folder under $build_directory, and for every *.box found:
        1. retrieve its version
        2. upload to atlas with this version
    NOTICE:
        1. Box version is calculated from box file name.
        2. Box provider is hardcoded and default to virtualbox currently.
           If need to upload boxs of multi-provider, there should be a way
           to pass the provider information to this script.
    """

    box_files = common.find_specify_type_files(build_directory, ".box", depth=1)
    if len(box_files) == 0:
        print "No box found under {0}".format(build_directory)

    for full_file_path in box_files:
        if not atlas_version:
            if is_release:
                # Box file name is like "rackhd-ubuntu-14.04-1.2.3-20161207024UTC.box"
                # Extract 1.2.3-20161207024UTC only
                atlas_version = "-".join(full_file_path.split('/')[-1:][0].strip(".box").split('-')[3:])
            else:
                from datetime import datetime
                datatime_now_md = datetime.utcnow().strftime("0.%m.%d")
                atlas_version = datatime_now_md
        atlas.upload_handler(atlas_version, "virtualbox", full_file_path)

def main():
    """
    Upload all the vagrant boxs to Atlas.
    """
    try:
        args = parse_args(sys.argv[1:])
        is_release = False
        if args.is_release == "true" or args.is_release == "True":
            is_release = True
        atlas = Atlas(args.atlas_url, args.atlas_username, args.atlas_name, args.atlas_token)
        upload_boxs(args.build_directory, atlas, is_release, args.atlas_version)
    except Exception, e:
        print e
        sys.exit(1)

if __name__ == '__main__':
    main()
