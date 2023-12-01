# Copyright (c) Quectel Wireless Solution, Co., Ltd.All Rights Reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import utime
import usys
import _thread
import osTimer


class Lock(object):

    def __init__(self):
        self.__lock = _thread.allocate_lock()
        self.__owner = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *args, **kwargs):
        self.release()

    def acquire(self):
        flag = self.__lock.acquire()
        self.__owner = _thread.get_ident()
        return flag

    def release(self):
        self.__owner = None
        return self.__lock.release()

    def locked(self):
        return self.__lock.locked()

    @property
    def owner(self):
        return self.__owner


class Waiter(object):
    """WARNING: Waiter object can only be used once."""

    def __init__(self):
        self.__lock = Lock()
        self.__lock.acquire()
        self.__gotit = True

    @property
    def unlock_timer(self):
        timer = getattr(self, '__unlock_timer__', None)
        if timer is None:
            timer = osTimer()
            setattr(self, '__unlock_timer__', timer)
        return timer

    def __auto_release(self, _):
        if self.__release():
            self.__gotit = False
        else:
            self.__gotit = True

    def acquire(self, timeout=-1):
        """timeout <= 0 for blocking forever."""
        if not self.__lock.locked():
            raise RuntimeError('Waiter object can only be used once.')
        self.__gotit = True
        if timeout > 0:
            self.unlock_timer.start(timeout * 1000, 0, self.__auto_release)
        self.__lock.acquire()  # block here
        if timeout > 0:
            self.unlock_timer.stop()
        self.__release()
        return self.__gotit

    def __release(self):
        try:
            self.__lock.release()
        except RuntimeError:
            return False
        return True

    def release(self):
        return self.__release()


class Condition(object):

    def __init__(self, lock=None):
        if lock is None:
            lock = Lock()
        self.__lock = lock
        self.__waiters = []
        self.acquire = self.__lock.acquire
        self.release = self.__lock.release

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *args, **kwargs):
        self.release()

    def __is_owned(self):
        return self.__lock.locked() and self.__lock.owner == _thread.get_ident()

    def wait(self, timeout=None):
        if not self.__is_owned():
            raise RuntimeError('cannot wait on un-acquired lock.')
        waiter = Waiter()
        self.__waiters.append(waiter)
        self.release()
        gotit = False
        try:
            if timeout is None:
                gotit = waiter.acquire()
            else:
                gotit = waiter.acquire(timeout)
            return gotit
        finally:
            self.acquire()
            if not gotit:
                try:
                    self.__waiters.remove(waiter)
                except ValueError:
                    pass

    def wait_for(self, predicate, timeout=None):
        endtime = None
        remaining = timeout
        result = predicate()
        while not result:
            if remaining is not None:
                if endtime is None:
                    endtime = utime.time() + remaining
                else:
                    remaining = endtime - utime.time()
                    if remaining <= 0.0:
                        break
            self.wait(remaining)
            result = predicate()
        return result

    def notify(self, n=1):
        if not self.__is_owned():
            raise RuntimeError('cannot wait on un-acquired lock.')
        if n < 0:
            raise ValueError('invalid param, n should be >= 0.')
        waiters_to_notify = self.__waiters[:n]
        for waiter in waiters_to_notify:
            waiter.release()
            try:
                self.__waiters.remove(waiter)
            except ValueError:
                pass

    def notify_all(self):
        if not self.__is_owned():
            raise RuntimeError('cannot wait on un-acquired lock.')
        self.notify(n=len(self.__waiters))


class Event(object):

    def __init__(self):
        self.__flag = False
        self.__cond = Condition()

    def wait(self, timeout=None):
        with self.__cond:
            return self.__cond.wait_for(lambda: self.__flag, timeout=timeout)

    def set(self):
        with self.__cond:
            self.__flag = True
            self.__cond.notify_all()

    def clear(self):
        with self.__cond:
            self.__flag = False

    def is_set(self):
        with self.__cond:
            return self.__flag


class Semaphore(object):

    def __init__(self, value=1):
        if value < 0:
            raise ValueError("semaphore initial value must be >= 0")
        self.__value = value
        self.__cond = Condition()

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *args, **kwargs):
        self.release()

    def acquire(self, block=True, timeout=None):
        with self.__cond:
            if not block:
                if self.__value > 0:
                    self.__value -= 1
                    return True
                else:
                    return False
            elif timeout is not None and timeout <= 0:
                raise ValueError("'timeout' must be a positive number.")
            else:
                if self.__cond.wait_for(lambda: self.__value > 0, timeout=timeout):
                    self.__value -= 1
                    return True
                else:
                    return False

    def release(self, n=1):
        if n < 1:
            raise ValueError('n must be one or more')
        with self.__cond:
            self.__value += n
            self.__cond.notify(n)

    def clear(self):
        with self.__cond:
            self.__value = 0


class BoundedSemaphore(Semaphore):

    def __init__(self, value=1):
        super().__init__(value)
        self.__initial_value = value

    def release(self, n=1):
        if n < 1:
            raise ValueError('n must be one or more')
        with self.__cond:
            if self.__value + n > self.__initial_value:
                raise ValueError("Semaphore released too many times")
            self.__value += n
            self.__cond.notify(n)


class Queue(object):

    class Full(Exception):
        pass

    class Empty(Exception):
        pass

    def __init__(self, max_size=100):
        self.queue = []
        self.__max_size = max_size
        self.__lock = Lock()
        self.__not_empty = Condition(self.__lock)
        self.__not_full = Condition(self.__lock)

    def _put(self, item):
        self.queue.append(item)

    def put(self, item, block=True, timeout=None):
        with self.__not_full:
            if not block:
                if len(self.queue) >= self.__max_size:
                    raise self.Full
            elif timeout is not None and timeout <= 0:
                raise ValueError("'timeout' must be a positive number.")
            else:
                if not self.__not_full.wait_for(lambda: len(self.queue) < self.__max_size, timeout=timeout):
                    raise self.Full
            self._put(item)
            self.__not_empty.notify()

    def _get(self):
        return self.queue.pop(0)

    def get(self, block=True, timeout=None):
        with self.__not_empty:
            if not block:
                if len(self.queue) == 0:
                    raise self.Empty
            elif timeout is not None and timeout <= 0:
                raise ValueError("'timeout' must be a positive number.")
            else:
                if not self.__not_empty.wait_for(lambda: len(self.queue) != 0, timeout=timeout):
                    raise self.Empty
            item = self._get()
            self.__not_full.notify()
            return item

    def size(self):
        with self.__lock:
            return len(self.queue)

    def clear(self):
        with self.__lock:
            self.queue.clear()


class LifoQueue(Queue):

    def _put(self, item):
        self.queue.append(item)

    def _get(self):
        return self.queue.pop()


class PriorityQueue(Queue):

    @classmethod
    def __siftdown(cls, heap, startpos, pos):
        newitem = heap[pos]
        while pos > startpos:
            parentpos = (pos - 1) >> 1
            parent = heap[parentpos]
            if newitem < parent:
                heap[pos] = parent
                pos = parentpos
                continue
            break
        heap[pos] = newitem

    def _put(self, item):
        self.queue.append(item)
        self.__siftdown(self.queue, 0, len(self.queue) - 1)

    @classmethod
    def __siftup(cls, heap, pos):
        endpos = len(heap)
        startpos = pos
        newitem = heap[pos]
        childpos = 2 * pos + 1
        while childpos < endpos:
            rightpos = childpos + 1
            if rightpos < endpos and not heap[childpos] < heap[rightpos]:
                childpos = rightpos
            heap[pos] = heap[childpos]
            pos = childpos
            childpos = 2 * pos + 1
        heap[pos] = newitem
        cls.__siftdown(heap, startpos, pos)

    def _get(self):
        lastelt = self.queue.pop()
        if self.queue:
            returnitem = self.queue[0]
            self.queue[0] = lastelt
            self.__siftup(self.queue, 0)
            return returnitem
        return lastelt

    @classmethod
    def convert(cls, sequence):
        n = len(sequence)
        for i in reversed(range(n // 2)):
            cls.__siftup(sequence, i)
        self = cls()
        self.queue = sequence
        return self


class _Result(object):

    class TimeoutError(Exception):
        pass

    def __init__(self):
        self.__rv = None
        self.__exc = None
        self.__finished = Event()

    def set(self, exc=None, rv=None):
        self.__exc = exc
        self.__rv = rv
        self.__finished.set()

    def get(self, timeout=None):
        if self.__finished.wait(timeout=timeout):
            if self.__exc:
                raise self.__exc
            return self.__rv
        else:
            raise self.TimeoutError('get result timeout.')


class Thread(object):

    def __init__(self, target=None, args=(), kwargs=None):
        self.__target = target
        self.__args = args
        self.__kwargs = kwargs or {}
        self.__ident = None

    def __repr__(self):
        return '<Thread {}>'.format(self.__ident)

    def is_running(self):
        if self.__ident is None:
            return False
        else:
            return _thread.threadIsRunning(self.__ident)

    def start(self):
        if not self.is_running():
            result = _Result()
            self.__ident = _thread.start_new_thread(self.run, (result,))
            return result

    def stop(self):
        if self.is_running():
            _thread.stop_thread(self.__ident)
            self.__ident = None

    def run(self, result):
        try:
            rv = self.__target(*self.__args, **self.__kwargs)
        except Exception as e:
            usys.print_exception(e)
            result.set(exc=e)
        else:
            result.set(rv=rv)

    @property
    def ident(self):
        return self.__ident

    @classmethod
    def get_current_thread_ident(cls):
        return _thread.get_ident()


class Task(object):

    def __init__(self, target=None, args=(), kwargs=None, priority=0, name=''):
        self.__target = target
        self.__args = args
        self.__kwargs = kwargs or {}
        self.priority = priority
        self.name = name
        self.result = _Result()

    def __str__(self):
        return '<Task \"{}\",{}>'.format(self.name, self.priority)

    def __call__(self, *args, **kwargs):
        try:
            rv = self.__target(*self.__args, **self.__kwargs)
        except Exception as e:
            self.result.set(exc=e)
        else:
            self.result.set(rv=rv)

    def __lt__(self, other):
        return self.priority < other.priority


def _worker(work_queue):
    while True:
        try:
            task = work_queue.get()
            task()
        except Exception as e:
            usys.print_exception(e)


class ThreadPoolExecutor(object):

    def __init__(self, max_workers=4, enable_priority=False):
        if max_workers <= 0:
            raise ValueError('max_workers must be greater than 0.')
        self.__max_workers = max_workers
        self.__work_queue = PriorityQueue() if enable_priority else Queue()
        self.__threads = set()
        self.__lock = Lock()

    def submit(self, *args, **kwargs):
        if len(args) == 1 and isinstance(args[0], Task):
            task = args[0]
        else:
            task = Task(**kwargs)
        self.__work_queue.put(task)
        self.__adjust_thread_count()
        return task.result

    def __adjust_thread_count(self):
        with self.__lock:
            if len(self.__threads) < self.__max_workers:
                t = Thread(target=_worker, args=(self.__work_queue,))
                t.start()
                self.__threads.add(t)

    def shutdown(self):
        with self.__lock:
            for t in self.__threads:
                t.stop()
            self.__threads.clear()
