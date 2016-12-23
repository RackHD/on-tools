#!/usr/bin/env python
# Copyright 2016, EMC, Inc.

"""
This is a command line program that monitor repos tag updates.
When new tag appears, this script will write a property file contains new tag information.
So a record file which stored history tags in each line is necessary.

usage:
    ./on-tools/manifest-build-tools/HWIMO-BUILD.py \
    on-tools/manifest-build-tools/application/tag_change_monitor.py \
    --repo rackhd/on-http \
    --history_file workspace/on-http_tag_history
    --property_file workspace/property_file
    --credential CREDS

The required parameters:
    repo: user_name/repo_name that indicates which repo should be monitoring.
    history_file: A file stored one history tag in each line. If doesn't exists it will be created.
    property_file: A file used for downstream job. It's format is like this:
                  tag_name=release/1.2.3
                  commit=fb47e10......
                  repository=https://github.com/RackHD/......
                  Contains the newly added tags (comparing with the $hsitory_file), with those tags' 
                  corresponding commit/repository"

The optional parameters:
    credential, A env var name which stores user:password of github.
    If you run this scipt continually this parameter is needed, otherwise github will forbidden the api requests.
"""

import os
import sys
import argparse
import requests

class TagChangeMonitor(object):
    """
    A simple class that monitor repo tag updates.
    One monitor for one repo.
    """
    def __init__(self, repo, history_file, property_file, credential):
        self.api_url = "https://api.github.com"
        self.repo = repo
        self.history_file = history_file
        self.property_file = property_file
        if credential:
            user, password = os.environ[credential].split(':')
            self.auth = (user, password)
        else:
            self.auth = ()

        self.history = {}
        self.new_history = {}
        self.change = {}

        if os.path.isfile(history_file):
            with file(history_file, 'r') as f:
                for tag_commit in f.readlines():
                    commit = tag_commit.split()[0]
                    tags = tag_commit.split()[1:]
                    self.history[commit] = tags
                f.close()
        else:
            with file(history_file, 'w') as f:
                f.close()

    def handle_tag_monitor(self):
        """
        Do tag monitor job
        """
        tag_list = self.get_tags()
        self.parse_tag_info(tag_list)
        if self.change:
            self.write_property_file()
        self.write_history_file()

    def get_tags(self):
        """
        Get all tags of current repo.
        """
        list_tag_url = "/".join([self.api_url, "repos", self.repo, "tags"])
        if self.auth:
            resp = requests.get(list_tag_url, auth=self.auth)
        else:
            resp = requests.get(list_tag_url)
        if resp.ok:
            return resp.json()
        else:
            print "Get tags of repo {0} error.\n{1}".format(self.repo, resp.text)
            sys.exit(1)

    def parse_tag_info(self, tag_list):
        """
        Get tag change and generate new tag history record.
        """
        find_change = False
        contains_in_new = True
        for tag in tag_list:
            tag_name = tag['name']
            commit = tag['commit']['sha']

            if (not self.history.has_key(commit)) or \
                (tag_name not in self.history[commit]):
                if not find_change:
                    self.change[commit] = [tag_name]
                    find_change = True
                else:
                    contains_in_new = False

            if contains_in_new:
                if self.new_history.has_key(commit):
                    self.new_history[commit].append(tag_name)
                else:
                    self.new_history[commit] = [tag_name]
            else:
                contains_in_new = True

    def write_history_file(self):
        """
        Write new_history to history_file
        This can keep history file valid when deleting tags.
        """
        with file(self.history_file, 'w') as history_file_handler:
            for commit, tags in self.new_history.iteritems():
                tags.insert(0, commit)
                tags.append('\n')
                history_file_handler.write(" ".join(tags))

    def write_property_file(self):
        """
        For those tags "newly" detected for this run, write those tags' 
        information into a property file ( being used by downstream Jenkins job )
        """
        with file(self.property_file, 'w') as property_file_handler:
            for commit, tags in self.change.iteritems():
                output = ""
                output += "tag_name={0}\n".format(tags[0])
                output += "commit={0}\n".format(commit)
                output += "repository=https://github.com/{0}.git".format(self.repo)
                property_file_handler.write(output)


def parse_args(args):
    """
    Parse script arguments.
    :return: Parsed args for assignment
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('--repo',
                        required=True,
                        help="Indicates the repo",
                        action='store')

    parser.add_argument('--history_file',
                        required=True,
                        help="File stored tag history",
                        action='store')

    parser.add_argument('--property_file',
                        required=True,
                        help="Downstream file to use",
                        action='store')

    parser.add_argument('--credential',
                        help="github credits",
                        action='store')

    parsed_args = parser.parse_args(args)
    return parsed_args


def main():
    """
    Monitor tag change of on repo
    """
    try:
        args = parse_args(sys.argv[1:])
        tcm = TagChangeMonitor(args.repo, args.history_file, args.property_file, args.credential)
        tcm.handle_tag_monitor()
    except Exception, e:
        print e
        sys.exit(1)

if __name__ == '__main__':
    main()
