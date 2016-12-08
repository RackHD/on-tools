"""
Module to abstract operations to repository
"""
import os
import config
from gitbits import GitBit
from ParallelTasks import ParallelTasks
from common import *

class RepoCloner(ParallelTasks):
    """
    Do the actual work of checking out a git repository to the specifications
    given in the manifest file.
    Usage:
    cloner = RepoCloner(integer)
    # the cloner could add several tasks 
    cloner.add_task(data)
    # data should contain:
      'repo': {
              "repository": "https://github.com/RackHD/on-tools.git",  ##required
              "commit-id": xxx,                                        ##optional
              "branch": xxx                                            ##optional
      },
      'builddir': dest_dir,   # the location to check out the repository into
      'credentials': git_credential  # a list of Git credentials in URL:VARIABLE_NAME format

    # run tasks in parallel
    cloner.finish()
    # get the result of tasks
    results = cloner.get_results()
    """
    def add_task(self, data, name=None):
        """
        Place data for a specific build into the work queue.  The work is to be done in
        a separate process.   This method will return quickly, as soon as the data is placed
        into the queue.  No guarantees are made as to when the work will be completed.

        :param data:
        data should contain:
           'credentials': a list of Git credentials in URL:VARIABLE_NAME format
           'repo': a repository entry from a manifest file
           'builddir': the location to check out the repository into
        :param name: a unique key for used for storing results
        :return: nothing
        """
        if data is not None and 'repo' in data and 'repository' in data['repo']:
            name = data['repo']['repository']
            super(RepoCloner, self).add_task(data, name)
        else:
            raise ValueError("no repository entry in data: {0}".format(data))

    
    @staticmethod
    def _get_reset_value(repo):
        """
        Return the appropriate reset value for the given repository.   This may be none.
        The idea is that a commit-id is the most specific thing that can be specified, so
        use that if it's available.   A tag should be used if present and no commit-id is
        available.

        :param repo: a specific manifest repository
        :return: the value to use with git reset --hard
        """
        reset_id = None
        if 'commit-id' in repo and repo['commit-id'] != '':
            reset_id = repo['commit-id']
        elif 'tag' in repo:
            reset_id = repo['tag']
        return reset_id


    def do_one_task(self, name, data, results):
        """
        Perform the actual work of checking out a repository.   This portion of the
        task is performed in a subprocess, and may be performed in parallel with other
        instances.

        name and data will come from the values passed in to add_task()

        :param name:
        :param data:
        data should contain:
           'credentials': a list of Git credentials in URL:VARIABLE_NAME format
           'repo': a repository entry from a manifest file
           'builddir': the location to check out the repository into
        :param results: a shared dictionary for storing results and sharing them to the
                        parent process
        :return: None (all output data stored in results)
        """

        # make sure we have all of the right data that we need to start the build
        if name is None or data is None:
            raise ValueError("name or data not present")

        for key in ['repo', 'builddir']:
            if key not in data:
                raise ValueError("{0} key missing from data: {1}".format(key, data))

        repo = data['repo']
        if 'repository' not in repo:
            raise ValueError("no repository in work {0}".format(repo))

        # data validation okay, so start the work

        print "Starting checkout of {0}".format(name)

        # someplace to start storing results of the commands that will be run
        results['commands'] = []
        commands = results['commands']
        git = GitBit(verbose=False)
        if 'credentials' in data:
            for credential in data['credentials']:
                url, cred = credential.split(',', 2)
                git.add_credential_from_variable(url, cred)
        repo_url = repo['repository']
        destination_directory_name = strip_suffix(os.path.basename(repo_url), ".git")
        # build up a git clone command line
        # clone [ -b branchname ] repository_url [ destination_name ]

        command = ['clone']

        #clone big files with git-lfs is much faster
        if repo.has_key('lfs') and repo['lfs']:
            command = ['lfs', 'clone']

        if 'branch' in repo:
            command.extend(['-b', repo['branch']])

        command.append(repo_url)

        if 'checked-out-directory-name' in repo:
            # this specifies what the directory name of the checked out repository
            # should be, as opposed to using Git's default (the basename of the repository URL)

            # note to self: do not combine the following two lines again
            destination_directory_name = repo['checked-out-directory-name']
            command.append(destination_directory_name)

        return_code, out, err = git.run(command, data['builddir'])

        commands.append({'command': command,
                         'return_code': return_code,
                         'stdout': out,
                         'stderr': err
                        })

        if return_code != 0:
            raise RuntimeError("Unable to clone the repository")

        # the clone has been performed -- now check to see if we need to move the HEAD
        # to point to a specific location within the tree history.   That will be true
        # if there is a commit-id or tag value specified in the repository (which will
        # be the case most of the time).

        reset_id = self._get_reset_value(repo)

        if reset_id is not None:
            working_directory = os.path.join(data['builddir'], destination_directory_name)

            command = ["reset", "--hard", reset_id]
            return_code, out, err = git.run(command, directory=working_directory)
            commands.append({'command': command,
                             'return_code': return_code,
                             'stdout': out,
                             'stderr': err
                            })
            if return_code != 0:
                raise RuntimeError("unable to move to correct commit/tag")

        results['status'] = "success"


class RepoOperator(object):

    def __init__(self, git_credentials=None):
        """
        Create a repository interface object

        :return:
        """
        self._git_credentials = git_credentials
        
        self.git = GitBit(verbose=True)
        if self._git_credentials:
            self.setup_gitbit()


    def setup_gitbit(self, credentials=None):
        """
        Set gitbit credentials.
        :return:
        """
        self.git.set_identity(config.gitbit_identity['username'], config.gitbit_identity['email'])
        if credentials is None:
            if self._git_credentials is None:
                return
            else:
                credentials = self._git_credentials
        else:
            self._git_credentials = credentials
        for url_cred_pair in credentials:
            url, cred = url_cred_pair.split(',')
            self.git.add_credential_from_variable(url, cred)

    def set_git_dryrun(self, dryrun):
        self.git.set_dryrun(dryrun)
    
    def set_git_verbose(self, verbose):
        self.git.set_verbose(verbose)

    def set_git_executable(self, executable):
        self.git.set_excutable(excutable)

    @staticmethod
    def print_command_summary(name, results):
        """
        Print the results of running commands.
          first the command line itself
            and the error code if it's non-zero
          then the stdout & stderr values from running that command

        :param name:
        :param results:
        :return: True if any command exited with an error condition
        """

        error_found = False

        print "============================"
        print "Command output for {0}".format(name)

        if 'commands' in results[name]:
            commands = results[name]['commands']
            for command in commands:
                for key in ['command', 'stdout', 'stderr']:
                    if key in command:
                        if command[key] != '':
                            print command[key]
                        if key == 'command':
                            if command['return_code'] != 0:
                                error_found = True
                                print "EXITED: {0}".format(command['return_code'])

        return error_found

    def clone_repo_list(self, repo_list, dest_dir, jobs=1):
        """
        check out repository to dest dir based on repo list
        :param repo_list: a list of repository entry which should contain:
                          'repository': the url of repository, it is required
                          'branch': the branch to be check out, it is optional
                          'commit-id': the commit id to be reset, it is optional
        :param dest_dir: the directory where repository will be check out
        :param jobs: Number of parallel jobs to run
        :return:
        """
        cloner = RepoCloner(jobs)
        if cloner is not None:
            for repo in repo_list:
                data = {'repo': repo,
                        'builddir': dest_dir,
                        'credentials': self._git_credentials
                       }
                cloner.add_task(data)
            cloner.finish()
            results = cloner.get_results()

            error = False
            for name in results.keys():
                error |= self.print_command_summary(name, results)

            if error:
                raise RuntimeError("Failed to clone repositories")

    def clone_repo(self, repo_url, dest_dir, repo_commit="HEAD"):
        """
        check out a repository to dest directory from the repository url
        :param repo_url: the url of repository, it is required
        :param dest_dir: the directory where repository will be check out
        :return: the directory of the repository
        """
        repo = {}
        repo["repository"] = repo_url
        repo["commit-id"] = repo_commit
        repo_list = [repo]
        self.clone_repo_list(repo_list, dest_dir)
        
        repo_directory_name = strip_suffix(os.path.basename(repo_url), ".git")
        return os.path.join(dest_dir, repo_directory_name)

    def get_lastest_commit_date(self, repo_dir):
        """
        :param repo_dir: path of the repository
        :return: commit-date
        """
        if repo_dir is None or not os.path.isdir(repo_dir):
            raise RuntimeError("The repository directory is not a directory")
        return_code, output, error = self.git.run(['show', '-s', '--pretty=format:%ct'], directory=repo_dir)
        if return_code == 0:
            return output.strip()
        else:
            raise RuntimeError("Unable to get commit date in directory {0}".format(repo_dir))

    def get_lastest_commit_id(self, repo_dir):
        """
        :param repo_dir: path of the repository
        :return: commit-id
        """
         
        if repo_dir is None or not os.path.isdir(repo_dir):
            raise RuntimeError("The repository directory is not a directory")

        return_code, output, error = self.git.run(['log', '--format=format:%H', '-n', '1'], directory=repo_dir)

        if return_code == 0:
            return output.strip()
        else:
            raise RuntimeError("Unable to get commit id in directory {0}".format(repo_dir))

    def get_lastest_commit_before_date(self, repo_dir, date):
        if repo_dir is None or not os.path.isdir(repo_dir):
            raise RuntimeError("The repository directory is not a directory")
        return_code, output, error = self.git.run(['log', '--format=format:%H', '--before='+date, '-n', '1'], directory=repo_dir)

        if return_code == 0:
            return output.strip()
        else:
            raise RuntimeError("Unable to get commit id before {date} in directory {repo_dir}"\
                  .format(date=date, repo_dir=repo_dir))

    def get_commit_message(self, repo_dir, commit):
        """
        :param repo_dir: path of the repository
        :param commit: the commit id of the repository
        :return: commit-message
        """

        if repo_dir is None or not os.path.isdir(repo_dir):
            raise RuntimeError("The repository directory is not a directory")

        return_code, output, error = self.git.run(['log', '--format=format:%B', '-n', '1', commit], directory=repo_dir)

        if return_code == 0:
            return output.strip()
        else:
            raise RuntimeError("Unable to get commit message of {commit_id} in directory {repo_dir}"\
                  .format(commit_id=commit, repo_dir=repo_dir))


    def get_repo_url(self, repo_dir):
        """
        get the remote url of the repository
        :param repo_dir: the directory of the repository
        :return: repository url
        """

        if repo_dir is None or not os.path.isdir(repo_dir):
            raise RuntimeError("The repository directory is not a directory")

        return_code, output, error = self.git.run(['ls-remote', '--get-url'], directory=repo_dir)

        if return_code == 0:
            return output.strip()
        else:
            raise RuntimeError("Unable to find the repository url in directory {0}".format(repo_dir))

    def get_current_branch(self, repo_dir):
        """
        get the current branch name of the repository
        :param repo_dir: the directory of the repository
        :return: branch name
        """

        if repo_dir is None or not os.path.isdir(repo_dir):
            raise RuntimeError("The repository directory is not a directory")

        return_code, output, error = self.git.run(['symbolic-ref', '--short', 'HEAD'], directory=repo_dir)

        if return_code == 0:
            return output.strip()
        else:
            raise RuntimeError("Unable to find the current branch in directory {0}".format(repo_dir))

    def check_branch(self, repo_url, branch):
        """
        Checks if the specified branch name exists for the provided repository. Leave only the characters
        following the final "/". This is to handle remote repositories.
        Raise RuntimeError if it is not found.
        :return: None
        """
        if "/" in branch:
            sliced_branch = branch.split("/")[-1]
        else:
            sliced_branch = branch

        return_code, output, error = self.git.run(['ls-remote', repo_url, 'heads/*{0}'.format(sliced_branch)])

        if return_code is not 0 or output is '':
            raise RuntimeError("The branch, '{0}', provided for '{1}', does not exist."
                               .format(branch, repo_url))

    def set_repo_tagname(self, repo_url, repo_dir, tag_name):
        """
        Sets tagname on the repo
        :param repo_url: the url of the repository
        :param repo_dir: the directory of the repository
        :param tag_name: the tag name to be set
        :return: None
        """
        # See if that tag exists for the repo
        return_code, output, error  = self.git.run(["tag", "-l", tag_name], repo_dir)

        # Raise RuntimeError if tag already exists, otherwise create it
        if return_code == 0 and output != '':
            raise RuntimeError("Error: Tag {0} already exists - exiting now...".format(output))
        else:
            print "Creating tag {0} for repo {1}".format(tag_name, repo_url)
            self.git.run(["tag", "-a", tag_name, "-m", "\"Creating new tag\""], repo_dir)
            self.git.run(["push", "origin", "--tags"], repo_dir)

    def create_repo_branch(self, repo_url, repo_dir, branch_name):
        """
        Creates branch on the repo
        :param repo_url: the url of the repository
        :param repo_dir: the directory of the repository
        :param branch_name: the branch name to be set
        :return: None
        """
        # See if that branch exists for the repo
        return_code, output, error  = self.git.run(["ls-remote", "--exit-code", "--heads", repo_url, branch_name], repo_dir)
        # Raise RuntimeError if branch already exists, otherwise create it
        if return_code == 0 and output != '':
            raise RuntimeError("Error: Branch {0} already exists - exiting now...".format(output))
        else:
            print "Creating branch {0} for repo {1}".format(branch_name, repo_url)
            return_code, output, error = self.git.run(["branch", branch_name], repo_dir)
            if return_code != 0:
                print output
                raise RuntimeError("Error: Failed to create local branch {0} with error: {1}.".format(branch_name, error))
            return_code, output, error = self.git.run(["push", "-u", "origin", branch_name], repo_dir)
            if return_code != 0:
                print output
                raise RuntimeError("Error: Failed to publish local branch {0} with error: {1}".format(branch_name, error))

    def checkout_repo_branch(self, repo_dir, branch_name):
        """
        Check out to specify branch on the repo
        :param repo_dir: the directory of the repository
        :param branch_name: the branch name to be checked
        :return: None
        """
        return_code, output, error  = self.git.run(["checkout", branch_name], repo_dir)

        if return_code != 0:
            raise RuntimeError("Error: Failed to checkout branch {0}".format(output))

    def push_repo_changes(self, repo_dir, commit_message, push_all=False):
        """
        publish changes of reposioty
        :param repo_dir: the directory of the repository
        :param commit_message: the message to be added to commit
        :return: None
        """

        status_code, status_out, status_error = self.git.run(['status'], repo_dir)
        if status_code == 0:
            if "nothing to commit, working directory clean" in status_out:
                print status_out
                return

        if push_all:
            add_code, add_out, add_error = self.git.run(['add', '-A'], repo_dir)
        else:
            add_code, add_out, add_error = self.git.run(['add', '-u'], repo_dir)

        if add_code != 0:
            raise RuntimeError('Unable to add files for commiting.\n{0}\n{1}\n{2}'.format\
                                 (add_code, add_out, add_error))

        commit_code, commit_out, commit_error = self.git.run(['commit', '-m', commit_message], repo_dir)
        if commit_code != 0:
            raise RuntimeError('Unable to commit changes for pushing.\n{0}\n{1}\n{2}'.format\
                                 (commit_code, commit_out, commit_error))

        push_code, push_out, push_error = self.git.run(['push'], repo_dir)
        if push_code !=0:
            raise RuntimeError('Unable to push changes.\n{0}\n{1}\n{2}'.format(push_code, push_out, push_error))
        return
