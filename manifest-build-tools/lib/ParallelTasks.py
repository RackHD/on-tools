# Copyright 2016, EMC, Inc.

import datetime
import os
import sys

if os.name == 'posix' and sys.version_info[0] < 3:
    import subprocess32 as subprocess
else:
    import subprocess

import multiprocessing

class ParallelTasks(object):
    """
    Run a set of tasks in parallel, collecting the output from each task (stdout & stderr), along
    with the process exit code, the child process ID and the start/end/elapsed time of each task.

    This class is intended to be subclassed, where the subclass will provide the specific code
    to be run for each task.   The do_one_task method will be called once per task, in a child
    process.   Various timing and other housekeeping results will be collected without the
    assistance of the do_one_task method.

    All results will be returned in a dictionary shared amongst all processes.   The do_one_task
    should populate the passed in results dictionary, which will then be collected by the parent
    and saved per-child, using the passed in task name as the key.

    """
    def __init__(self, job_count):
        if job_count < 1:
            job_count = 1

        self._notification_queue = multiprocessing.JoinableQueue()
        self._manager = multiprocessing.Manager()
        self._shared_results = self._manager.dict()

        self._processes = [multiprocessing.Process(target=self._run_task_queue)
                           for i in range(job_count)
                          ]

        for process in self._processes:
            process.start()


    def get_results(self):
        """
        Return the current result status from all subprocesses that have completed
        :return: subprocess results, keyed via 'name' passed in to add_task
        """
        return self._shared_results


    def add_task(self, data, name):
        """
        Initiate the checkout process -- this notifies the worker queue that a
        specific repository needs to be checked out

        :param data: arbitrary data to be passed to a worker child process
        :param name: the key by which this data's job results will be returned
        """
        if data is None or name is None:
            raise ValueError ("no task parameter may be none")

        if self._notification_queue is None:
            raise RuntimeError("no notification queue available")

        self._notification_queue.put((name, data))


    def _run_task_queue(self):
        """
        Continually check the notification queue for work to do, and then do it
        :return:

        This function will run forever.   When there are no more items in the work queue,
        the main process will terminate all of the child processes, which will all be waiting
        on Queue.get() to return a value (which won't be coming)

        """
        while True:
            (name,data) = self._notification_queue.get()

            if name is None or data is None:
                raise ValueError("will not run a job without name or data")

            results = { 'task': {}}
            results['task']['start_time'] = datetime.datetime.now()
            results['task']['name'] = name
            results['task']['pid'] = os.getpid()
            results['task']['ppid'] = os.getppid()

            try:
                self.do_one_task(name, data, results)
            except Exception as ex: # pylint: disable=broad-except
                results['exception'] = ex
                results['status'] = 'exception'
            except: # catch *all* exceptions # pylint: disable=bare-except
                results['error'] = sys.exc_info()[0]
                results['status'] = 'error'

            self._shared_results[name] = results

            results['task']['end_time'] = datetime.datetime.now()
            results['task']['elapsed_time'] = results['task']['end_time'] - results['task']['start_time']

            self._notification_queue.task_done()

    def do_one_task(self, name, data, results):
        """
        Perform the actual work.  This portion of the task is performed in a
        subprocess, and may be performed in parallel with other instances.

        The specific data to be passed to the child process is passed in via data.

        Results should be returned via the results dictionary parameter, and should be
        entesavedred via a key named by name.  The resulting data will normally
        be a dictionary of multiple values

        :return: any calculated results via results dictionary
        """
        # example usage might be
        #  results[name]['value'] = calculate_value_from(data)

        raise NotImplementedError("__do_one_task must be implemented by a subclass")


    def finish(self):
        """
        Wait for all of the subprocesses to complete all assigned tasks.

        :return: none
        """

        # Block until all items in the queue have been gotten and processed.
        self._notification_queue.join()

        # so now we can do through all of the child processes and stop them
        # (extreme prejudice is okay, since all work has been performed and they're
        # just waiting on the queue.get() operation).
        for process in self._processes:
            process.terminate()

