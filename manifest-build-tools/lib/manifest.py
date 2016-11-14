# Copyright 2016, EMC, Inc.

"""
Module to abstract a manifest file
"""
import json
import os
import re
import sys
import datetime
import config

from gitbits import GitBit


class Manifest(object):
    def __init__(self, file_path, git_credentials = None):
        """
        __build_name - Refer to the field "build-name" in manifest file.
        __repositories - Refer to the field "repositories" in manifest file.
        __downstream_jobs - Refer to the field "downstream-jobs" in manifest file.
        __file_path - The file path of the manifest file
        __name - The file name of the manifest file
        __manifest -The content of the manifest file
        __git_credentials  - URL, credentials pair for the access to github repos
        gitbit - Class instance of gitbit
        """

        self._build_name = None
        self._build_requirements = None
        self._repositories = []
        self._downstream_jobs = []
        self._file_path = file_path
        self._name = file_path.split('/')[-1]
        self._manifest = None

        self._git_credentials = None
        self.gitbit = GitBit(verbose=True)

        if git_credentials:
            self._git_credentials = git_credentials
            self.setup_gitbit()

        self.read_manifest_file(self._file_path)
        self.parse_manifest()

    def set_git_credentials(self, git_credentials):
        self._git_credentials.append = git_credentials
        self.setup_gitbit()

    def get_downstream_jobs(self):
        return self._downstream_jobs

    def get_repositories(self):
        return self._repositories

    def get_manifest(self):
        return self._manifest

    def get_name(self):
        return self._name

    def get_file_path(self):
        return self._file_path

    def get_build_name(self):
        return self._build_name

    def set_build_name(self, build_name):
        self._manifest['build-name'] = build_name
        self._build_name = build_name
        
    def get_build_requirements(self):
        return self._build_requirements

    def set_build_requirements(self, requirements):
        self._manifest['build-requirements'] = requirements
        self._build_requirements = requirements

    def setup_gitbit(self):
        """
        Set gitbit credentials.
        :return: None
        """
        self.gitbit.set_identity(config.gitbit_identity['username'], config.gitbit_identity['email'])
        if self._git_credentials:
            for url_cred_pair in self._git_credentials:
                url, cred = url_cred_pair.split(',')
                self.gitbit.add_credential_from_variable(url, cred)

    def read_manifest_file(self, filename):
        """
        Reads the manifest file json data to class member _manifest.
        :param filename: where to read the manifest data from
        :return: None
        """
        if not os.path.isfile(filename):
            raise KeyError("No file found for manifest at {0}".format(filename))

        with open(filename, "r") as manifest_file:
            self._manifest = json.load(manifest_file)

    def parse_manifest(self):
        """
        parse manifest and assign properties
        :return: None
        """
        if 'build-name' in self._manifest:
            self._build_name = self._manifest['build-name']
  
        if 'build-requirements' in self._manifest:
            self._build_requirements = self._manifest['build-requirements']

        if 'repositories' in self._manifest:     
            for repo in self._manifest['repositories']:
                self._repositories.append(repo)

        if 'downstream-jobs' in self._manifest:
            for job in self._manifest['downstream-jobs']:
                self._downstream_jobs.append(job)

    @staticmethod
    def validate_repositories(repositories):
        """
        validate whether the entry 'repositories' contains useful information
        return: True if the entry is valid,
                False if the entry is unusable
                and message including omission imformation
        """
        result = True
        message = []
        for repo in repositories:
            valid = True
            # repository url is required
            if 'repository' not in repo:
                valid = False
                message.append("entry without tag repository")

            # either branch or commit-id should be set.
            if 'branch' not in repo and \
               'commit-id' not in repo:
                valid = False
                message.append("Either branch or commit-id should be set for entry")

            if not valid:
                result = False
                message.append("entry content:")
                message.append("{0}".format(json.dumps(repo, indent=True)))
        
        return result, message

    @staticmethod
    def validate_downstream_jobs(downstream_jobs):
        """
        validate whether the entry 'downstream-jobs' contains useful information
        return: True if the entry is valid,
                False if the entry is unusable
                and message including omission imformation
        """
        result = True
        message = []
        for job in downstream_jobs:
            valid = True
            # repository url is required
            if 'repository' not in job:
                valid = False
                message.append("entry without tag repository")

            #command is required
            if 'command' not in job:
                valid = False
                message.append("entry without tag command")

            #working-directory is required
            if 'working-directory' not in job:
                valid = False
                message.append("entry without tag working-directory")

            #running-label is required
            if 'running-label' not in job:
                valid = False
                message.append("entry without tag running-label")

            # either branch or commit-id should be set.
            if 'branch' not in job and \
               'commit-id' not in job:
                valid = False
                message.append("Either commit-id or branch should be set for job repository")

            # downstream-jobs is optional
            # if it is specified, the value should be validate
            if 'downstream-jobs' in job:
                downstream_result, downstream_message = Manifest.validate_downstream_jobs(job['downstream-jobs'])
                if not downstream_result:
                    valid = False
                    message.extend(downstream_message)

            if not valid:
                result = False
                message.append("entry content:")
                message.append("{0}".format(json.dumps(job, indent=True)))

        return result, message

    def validate_manifest(self):
        """
        Identify whether the manifest contains useful information (as we understand it)
        raise error if manifest is unusable
        :return: None
        """

        result = True
        messages = ["Validate manifest file: {0}".format(self._name)]
        if self._manifest is None:
            result = False
            messages.append("No manifest contents")

        #build-name is required
        if 'build-name' not in self._manifest:
            result = False
            messages.append("No build-name in manifest file")

        #repositories is required
        if 'repositories' not in self._manifest:
            result = False
            messages.append("No repositories in manifest file")
        else:
            r, m = self.validate_repositories(self._repositories)
            if not r:
                result = False
                messages.extend(m)
        #downstream-jobs is required
        if 'downstream-jobs' not in self._manifest:
            result = False
            messages.append("No downstream-jobs in manifest file")
        else:
            r, m = Manifest.validate_downstream_jobs(self._downstream_jobs)
            if not r:
                result = False
                messages.extend(m)
        #build-requirements is required
        if 'build-requirements' not in self._manifest:
            result = False
            messages.append("No build-requirements in manifest file")
        
        if not result:
            messages.append("manifest file {0} is not valid".format(self._name))
            error = '\n'.join(message)
            raise KeyError(error)

