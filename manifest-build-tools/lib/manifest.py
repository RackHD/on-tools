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

manifest_sample = "manifest.json"
class Manifest(object):
    def __init__(self, file_path, git_credentials = None):
        """
        __build_name - Refer to the field "build-name" in manifest file.
        __repositories - Refer to the field "repositories" in manifest file.
        __downstream_jobs - Refer to the field "downstream-jobs" in manifest file.
        __file_path - The file path of the manifest file
        __name - The file name of the manifest file
        __manifest -The content of the manifest file
        __changed - If manifest is changed, be True; The default value is False
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
        self._changed = False

        self._git_credentials = None
        self.gitbit = GitBit(verbose=True)

        if git_credentials:
            self._git_credentials = git_credentials
            self.setup_gitbit()

        self.read_manifest_file(self._file_path)
        self.parse_manifest()

    @staticmethod
    def instance_of_sample():
        repo_dir = os.path.dirname(sys.path[0])
        for subdir, dirs, files in os.walk(repo_dir):
            for file in files:
                if file == manifest_sample:
                    manifest = Manifest(os.path.join(subdir, file))
                    return manifest
        return None

    def set_git_credentials(self, git_credentials):
        self._git_credentials = git_credentials
        self.setup_gitbit()

    @property
    def downstream_jobs(self):
        return self._downstream_jobs

    @property
    def repositories(self):
        return self._repositories

    @property
    def manifest(self):
        return self._manifest

    @property
    def name(self):
        return self._name

    @property
    def file_path(self):
        return self._file_path

    @property
    def build_name(self):
        return self._build_name

    @build_name.setter
    def build_name(self, build_name):
        self._build_name = build_name
        self._manifest['build-name'] = build_name

    @property
    def build_requirements(self):
        return self._build_requirements
    
    @build_requirements.setter
    def build_requirements(self, requirements):
        self._manifest['build-requirements'] = requirements
        self._build_requirements = requirements

    @property
    def changed(self):
        return self._changed

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
            if 'repository' not in repo or repo['repository'] == "":
                valid = False
                message.append("entry without tag repository")

            # either branch or commit-id should be set.
            if ('branch' not in repo or repo['branch'] == "") and \
               ('commit-id' not in repo or repo['commit-id'] == ""):
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
            if 'repository' not in job or job['repository'] == "":
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
            if ('branch' not in job or job['branch'] == "") and \
               ('commit-id' not in job or job['commit-id'] == ""):
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
            error = '\n'.join(messages)
            raise KeyError(error)

    @staticmethod
    def check_commit_changed(repo, repo_url, branch, commit):
        """
        Check whether the repository is changed based on its url, branch ,commit-id and arguments repo_url, branch, commit
        :param repo: an repository entry of member _repositories or _downstream_jobs
        :param repo_url: the url of the repository
        :param branch: the branch of the repository
        :param commit: the commit id of the repository
        :return: True when the commit-id is different with argument commit
                 and the url and branch is the same with the arguments repo_url, branch;
                 otherwise, False
        """

        if (repo['repository'] == repo_url):
            # If repo has "branch", compare "commit-id" in repo with the argument commit
            # only when "branch" is the same with argument branch.

            if 'branch' in repo:
                sliced_repo_branch = repo['branch'].split("/")[-1]
                sliced_branch = branch.split("/")[-1]
                if (repo['branch'] == branch or
                    repo['branch'] == sliced_branch or
                    sliced_repo_branch == sliced_branch):

                    if 'commit-id' in repo:
                        print "checking the commit-id for {0} with branch {1} from {2} to {3}".format\
                                (repo_url, branch, repo['commit-id'], commit)

                        if repo['commit-id'] != commit:
                            print "   commit-id updated!"
                            return True
                        else:
                            print "   commit-id unchanged"
                            return False
                    else:
                        print "add commit-id{0} for {1} with branch {2} ".format\
                              (commit, repo_url, branch)
                        return True
            # If repo doesn't have "branch", compare "commit-id" in repo with argument commit
            # Exits with 1 if repo doesn't have "commit-id"
            else:
                if 'commit-id' not in repo:
                    raise KeyError("Neither commit-id nor branch is set for repository {0}".format(repo['repository']))
                else:
                    if repo['commit-id'] != commit:
                        print "   commit-id updated!"
                        return True
                    else:
                        print "   commit-id unchanged"
                        return False
        return False

    @staticmethod
    def update_downstream_jobs(downstream_jobs, repo_url, branch, commit):
        """
        update the instance of the class based on member:
        _downstream_jobs and provided arguments.

        :param downstream_jobs: the entry downstream_jobs
        :param repo_url: the url of the repository
        :param branch: the branch of the repository
        :param commit: the commit id of the repository
        :return: True if any job in downstream_jobs is updated
                 False if none of jobs in downstream_jobs is updated
        """
        updated = False
        for job in downstream_jobs:
            if Manifest.check_commit_changed(job, repo_url, branch, commit):
                job['commit-id'] = commit
                updated = True
            if 'downstream-jobs' in job:
                nested_downstream_jobs = job['downstream-jobs']
                if Manifest.update_downstream_jobs(nested_downstream_jobs, repo_url, branch, commit):
                    updated = True
        return updated

    @staticmethod
    def update_repositories(repositories, repo_url, branch, commit):
        """
        update the instance of the class based on member:
        _repositories and provided arguments.

        :param repositories: the entry repositories
        :param repo_url: the url of the repository
        :param branch: the branch of the repository
        :param commit: the commit id of the repository
        :return:
        """
        updated = False
        for repo in repositories:
            if Manifest.check_commit_changed(repo, repo_url, branch, commit):
                repo['commit-id'] = commit
                updated = True
        return updated

    def update_manifest(self, repo_url, branch, commit):
        """
        update the instance of the class based on members
         _repositories , _downstream_jobs and provided arguments.
        :param repo_url: the url of the repository
        :param branch: the branch of the repository
        :param commit: the commit id of the repository
        :return:
        """
        print "start updating  manifest file {0}".format(self._name)
        if self.update_repositories(self._repositories, repo_url, branch, commit):
            self._changed = True

        if self.update_downstream_jobs(self._downstream_jobs, repo_url, branch, commit):
            self._changed = True

    def write_manifest_file(self, repo_dir, commit_message, file_path=None, dryrun=False):
        """
        Add, commit, and push the manifest changes to the manifest repo.
        :param repo_dir: String, The directory of the repository
        :param commit_message: String, The commit message for command "git commit"
        :param file_path: String, The path to the temporary file.
                          If it is not set, the default value is self._file_path where manifest come from
        :param dry_run: If true, would not push changes
        :return:
        """
        if file_path is None:
            file_path = self._file_path

        with open(file_path, 'w') as fp:
            json.dump(self._manifest, fp, indent=4, sort_keys=True)

        status_code, status_out, status_error = self.gitbit.run(['status'], repo_dir)
        add_code, add_out, add_error = self.gitbit.run(['add', '-u'], repo_dir)

        if add_code != 0:
            raise RuntimeError('Unable to add files for commiting.\n{0}\n{1}\n{2}}'.format\
                                 (add_code, add_out, add_error))

        commit_code, commit_out, commit_error = self.gitbit.run(['commit', '-m', commit_message], repo_dir)
        if commit_code != 0:
            raise RuntimeError('Unable to commit changes for pushing.\n{0}\n{1}\n{2}'.format\
                                 (commit_code, commit_out, commit_error))

        if not dryrun:
            push_code, push_out, push_error = self.gitbit.run(['push'], repo_dir)
            if push_code !=0:
                raise RuntimeError('Unable to push changes.\n{0}\n{1}\n{2}'.format(push_code, push_out, push_error))
        else:
            print "Would push changes here if not for dry run"
        return
