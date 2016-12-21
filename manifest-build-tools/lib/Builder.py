# Copyright 2016, DELLEMC, Inc.
"""
This is a module that contains the tool for python to run a list of commands
and generate report for results of running.
"""

import os
import subprocess
import sys

try:
    from ParallelTasks import ParallelTasks
    import common
except ImportError as import_err:
    print import_err
    sys.exit(1)

class BuildResult(object):
    """
    Complete output from the running of a build command on a given host.
    Contains the command that was supposed to be run, whether it was present ot not,
    the return code, and the standard output and standard error text.
    """
    def __init__(self, command, present, return_code=None, stdout=None, stderr=None):
        self._command = command
        self._present = present

        self._return_code = return_code
        self._stdout = stdout
        self._stderr = stderr

    @property
    def command(self):
        return self._command

    @command.setter
    def command(self, command):
        self._command = command

    @property
    def present(self):
        return self._present

    @present.setter
    def present(self, present):
        self._present = present

    @property
    def return_code(self):
        return self._return_code

    @return_code.setter
    def return_code(self, return_code):
        self._return_code = return_code

    @property
    def stdout(self):
        return self._stdout

    @stdout.setter
    def stdout(self, stdout):
        self._stdout = stdout

    @property
    def stderr(self):
        return self._stderr

    @stderr.setter
    def stderr(self, stderr):
        self._stderr = stderr

    def generate_detailed_report(self):
        """
        Generate reports with details: return code, stdout, stderr
        """
        detailed = []
        if self._present is True:
            detailed.append(self._command)
            if self._return_code != 0:
                detailed.append("  ERROR: EXIT {0}".format(self._return_code))
                if self._stdout is not None and self._stdout != "":
                    detailed.append(self._stdout)
                if self._stderr is not None and self._stderr != "":
                    detailed.append(self._stderr)

        return detailed

    def generate_summary_report(self):
        """
        Generate report with the result of running: 
        Good or ERROR: EXIT or Not Present
        """
        summary = []
        short_command = os.path.basename(self._command)
        if self._present is True:
            if self._return_code is not None:
                if self._return_code == 0:
                    status = "GOOD"
                else:
                    status = "ERROR: EXIT {0}".format(self._return_code)
            else:
                status = "RETURN CODE IS NONE"
        else:
            status = " Not Present"
        summary.append("    {0}: {1}".format(short_command, status))
        return summary

    @staticmethod
    def summarize_errors(results):
        errors = 0
        for result in results:
            if result.return_code != 0:
                errors += 1
        return errors

class BuildCommand(object):
    """
    A module for build command.
    """
    def __init__(self, name, directory, arguments=None, use_sudo=False, sudo_creds=None):
        """
        _name: the command name that was supposed to be run
        _directory: the directory under which to run command
        _use_sudo: whether the command was run with sudo previleges
        _sudo_creds: the environment variable name of sudo credentials. 
                     For example: SUDO_CREDS=username:password
        _arguments: the arguments of the command
        """
        self._name = name
        self._directory = directory
        self._use_sudo = use_sudo
        self._sudo_creds = sudo_creds
        self._arguments = arguments

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def directory(self):
        return self._directory

    @directory.setter
    def directory(self, directory):
        self._directory = directory

    @property
    def use_sudo(self):
        return self._use_sudo

    @use_sudo.setter
    def use_sudo(self, use_sudo):
        self._use_sudo = use_sudo

    @property
    def sudo_creds(self):
        return self._sudo_creds

    @sudo_creds.setter
    def sudo_creds(self, sudo_creds):
        self._sudo_creds = sudo_creds
        
    def to_string(self):
        cmd_args = []
        if self._use_sudo:
            if self._sudo_creds is None:
                raise ValueError("sudo credential missing from commands {0}".format(name))
            (username, password) = common.parse_credential_variable(self._sudo_creds)
            cmd_args += ["echo"]
            cmd_args += [password]
            cmd_args += ["|sudo -S"]

        cmd_args += [self._name]

        if self._arguments:
            cmd_args += self._arguments

        command_str = " ".join(cmd_args)
        return command_str

    def run(self):
        try:
            command = self.to_string()
            print "Execute command: {0} under {1}".format(command, self._directory)
            proc = subprocess.Popen(command,
                                    stderr=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    cwd=self._directory,
                                    shell=True)
            (out, err) = proc.communicate()
        except Exception, ex:
            # this is a terrible failure, not just process exit != 0
            return BuildResult(self._name,
                               present=True,
                               return_code=1,
                               stderr=ex)

        result = BuildResult(self._name,
                             present=True,
                             return_code=proc.returncode,
                             stdout=out,
                             stderr=err)
        return result

    def is_executable(self):
        exe_file = os.path.join(self._directory, self._name)
        if os.path.isfile(exe_file) and os.access(exe_file, os.X_OK):
            return True

        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if os.path.isfile(exe_file) and os.access(exe_file, os.X_OK):
                return True

        return False

class Builder(ParallelTasks):
    """
    Run a list of command under a directory.

    This class is intended for use with ParallelTasks, and each commands list may be done
    in a separate process.

    """
    def add_task(self, data, name):
        """
        Add a task to task queue
        :param data: A dictonary which should contain:
                     commands: A list of comamnd instances. It's required.
                     env_file: A property file which contains environment variables. It's optional
        :param name: The name of the task. The key by which the job results will be returned.
        :return: None
        """
        if data is None:
            raise ValueError("Task parameter data not present")

        if 'commands' not in data:
            raise ValueError("commands key missing from data: {0}".format(data))

        super(Builder, self).add_task(data, name)

    @staticmethod
    def initail_environment(env_file):
        print "start to export environment file {0}".format(env_file)
        if not os.path.isfile(env_file):
            raise RuntimeError("Failed to initial environment due to the file {0} doesn't exist"
                               .format(env_file))
        props = common.parse_property_file(env_file)
        if props:
            for item in props.items():
                key = item[0]
                value = item[1]
                os.environ[key] = value

    def do_one_task(self, name, data, results):
        """
        Perform the actual work.
        name and data will come from the values passed in to add_task()
        :param results: a list of instances of BuildResult
        :return: None
        """
        try:
            if 'command' not in results:
                results['command'] = []

            if 'env_file' in data and data['env_file'] is not None:
                self.initail_environment(data['env_file'])

            for command in data['commands']:
                if not command.is_executable():
                    build_result = BuildResult(command, present=False)
                build_result = command.run()
                if build_result is not None:
                    results['command'].append(build_result)

        except Exception, e:
            raise RuntimeError("Failed to do task {0} due to {1}".format(name, e))

    def summarize_results(self):
        """
        :return: True if the number of errors found is 0
                 False if the number of errors found is greater than 0
        """
        results = self.get_results()
        key_list = results.keys()

        for name in sorted(key_list):
            if 'command' in results[name]:
                build_results = results[name]['command']
                errors = BuildResult.summarize_errors(build_results)
                if errors > 0:
                    return False
        return True

    def generate_detailed_report(self):
        """
        Generate reports with details: return code, stdout, stderr
        """
        all_detailed = []
        results = self.get_results()
        key_list = results.keys()
        for name in sorted(key_list):
            if 'command' in results[name]:
                task_detailed = []
                task_detailed.append("=== Results for {0} ===".format(name))
                for result in results[name]['command']:
                    detailed = result.generate_detailed_report()
                    task_detailed.extend(detailed)

                all_detailed.extend(task_detailed)
        return all_detailed

    def generate_summary_report(self):
        """
        Generate report with the result of running:
        Good or ERROR: EXIT or Not Present
        """       
        all_summary = []

        results = self.get_results()
        key_list = results.keys()

        for name in sorted(key_list):
            if 'command' in results[name]:
                task_summary = []
                task_summary.append("{0}:".format(name))
                build_results = results[name]['command']
                errors = BuildResult.summarize_errors(build_results)
                if errors > 0:
                    task_summary.append("    Number of falied commands: {0}".format(errors))

                for result in build_results:
                    summary = result.generate_summary_report()
                    task_summary.extend(summary)

                all_summary.extend(task_summary)

        return all_summary

