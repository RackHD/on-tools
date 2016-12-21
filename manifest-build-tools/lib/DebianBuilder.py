"""
This is a module that contains the tool for python to build the
debians after all the directories are checked out based on a given manifest file.
"""
# Copyright 2016, EMC, Inc.

import os
import subprocess
import sys

try:
    from Builder import Builder
    from Builder import BuildCommand
except ImportError as import_err:
    print import_err
    sys.exit(1)

class DebianBuilder(object):
    """
    This is a class that builds the debian packages. 
    It assumes that the repository is cloned successfully and is accessible for the tool.
    """
    def __init__(self, top_level_dir, repos, jobs=1, sudo_creds=None):
        """
        :param top_level_dir: the directory that holds all the cloned
                              repositories according to manifest
                              example: <top_level_dir>/on-http/...
                                                      /on-tftp/...
        :param repos: a list of repositories to be build
        :param jobs: Number of parallel jobs(build debian packages) to run.
        :param sudo_creds: the environment variable name of sudo credentials.
                           for example: SUDO_CRED=username:password
        :return: None
        """
        self.top_level_dir = top_level_dir
        self._repos = repos
        self._jobs = jobs
        self._sudo_creds = sudo_creds
        self._builder = Builder(self._jobs)        

    @property
    def top_level_dir(self):
        return self._top_level_dir

    @top_level_dir.setter
    def top_level_dir(self, top_level_dir):
        """
        Setter for the repository directory
        :param top_level_dir: the directory that holds all the cloned
                              repositories according to manifest
                              example: <top_level_dir>/on-http/...
                                                      /on-tftp/...
        :return: None
        """
        if os.path.isdir(top_level_dir):
            self._top_level_dir = os.path.abspath(top_level_dir)
        else:
            raise ValueError("The path provided '{dir}' is not a directory."
                             .format(dir=top_level_dir))

    def generate_tasks(self):
        """
        Generate a list of tasks to be perform.
        An example of task:
                   {
                    'name': repo,
                    'data': {
                             'commands': [command1, ...], #command1 is an instance of BuildCommand
                             'env_file': on-http.version
                            }
                   }
        
        """
        tasks = []
        for repo in self._repos:
            task = {
                    'name': repo,
                    'data': {
                             'commands': [],
                             'env_file': None
                            }
                   }
            command_name = './HWIMO-BUILD'
            path = os.path.abspath(os.path.join(self._top_level_dir, repo))
            if not os.path.exists(path):
                raise ValueError("Repository {0} doesn't exist under {1}"
                                 .format(repo, self._top_level_dir))
            command = BuildCommand(command_name, path)
            if repo == "on-imagebuilder" and self._sudo_creds:
                command.use_sudo = True
                command.sudo_creds = self._sudo_creds
            task['data']['commands'].append(command)

            version_file = "{0}.version".format(repo)
            version_path = os.path.abspath(os.path.join(path, version_file))
            if os.path.exists(version_path):
                task['data']['env_file'] = version_path
            tasks.append(task)

        return tasks

    def blind_build_all(self):
        """
        Iterate through the first layer subdirectory of top_level_dir and
        if found HWIMO-BUILD, then execute the script.
        """
        try:
            tasks = self.generate_tasks()
            for task in tasks:
                self._builder.add_task(task['data'], task['name'])
            self._builder.finish()
        except Exception, e:
            raise RuntimeError("Failed to build all debian packages due to \n{0}".format(e))

    def get_build_result(self):
        """
        If all the tasks success, then return true,
        otherwise return false
        :return: True if build success.
                 False if build failed.
        """
        build_result = self._builder.summarize_results()
        return build_result

    def print_detailed_report(self):
        detailed = self._builder.generate_detailed_report()
        print "\n\nvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv\n\n"
        print "Full Details\n"
        for item in detailed:
            print item

    def print_summary_report(self):
        summary = self._builder.generate_summary_report()
        print "\n\n^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\n"
        print "Summary:"
        for item in summary:
            print item
        print "\n\n"

