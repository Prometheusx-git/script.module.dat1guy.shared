# -*- coding: utf-8 -*-
'''
    dat1guy's Shared Methods - a plugin for Kodi
    Copyright (C) 2016 dat1guy

    This file is part of dat1guy's Shared Methods.

    dat1guy's Shared Methods is free software: you can redistribute it and/or
    modify it under the terms of the GNU General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    dat1guy's Shared Methods is distributed in the hope that it will be 
    useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with dat1guy's Shared Methods.  If not, see 
    <http://www.gnu.org/licenses/>.
'''


'''
    BASED ON THE THREADPOOL IMPLEMENTATION FROM METACHRIS:
    https://www.metachris.com/2016/04/python-threadpool/

    Kodi's python does not handle daemon threads correctly, in that they cannot be left alive.
    Because they must be killed, the ThreadPool class no longer benefits from using the 
    producer/consumer Queue class, where put and get block on the size of the queue, indefinitely
    in this case.

    In order to die, the worker threads need to have some way of knowing when to die.  To that end,
    I made the following changes:
     - tasks are added to the list before starting the worker threads
     - worker threads use the thread-safe pop function to receive the tasks:
       http://effbot.org/pyfaq/what-kinds-of-global-value-mutation-are-thread-safe.htm
     - worker threads know they're done when they hit an IndexError: pop from empty list exception
     - worker threads set an Event object to signal to the main thread that they are done and 
       exiting
     - the main thread waits on each worker's Event objects, in effect waiting until they are all 
       done
'''


from threading import Thread, Event


class Worker(Thread):
    def __init__(self, tasks):
        Thread.__init__(self)
        self.tasks = tasks
        self.done = Event()

    ''' PUBLIC FUNCTIONS '''
    def run(self):
        while True:
            try:
                func, args, kargs = self.tasks.pop()
            except IndexError:
                self.done.set()
                return

            try:
                func(*args, **kargs)
            except Exception as e:
                print(e)

class ThreadPool:
    """ Pool of threads consuming tasks from a task list """
    def __init__(self, num_threads):
        self.tasks = []
        self.workers = []
        for _ in range(num_threads):
            self.workers.append(Worker(self.tasks))

    ''' PUBLIC FUNCTIONS '''
    def map(self, func, args_list):
        """ Add a list of tasks to the task list and start the threads """
        map(lambda args: self._add_task(func, args), args_list)
        map(lambda worker: worker.start(), self.workers)

    def wait_completion(self):
        """ Wait for completion of all the tasks in the task list """
        map(lambda worker: worker.done.wait(), self.workers)

    ''' PROTECTED FUNCTIONS '''
    def _add_task(self, func, *args, **kargs):
        """ Add a task to the task list """
        self.tasks.append((func, args, kargs))