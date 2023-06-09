import time

import git
from os import chmod
from os.path import exists, join
from tempfile import gettempdir

from fasteners.process_lock import InterProcessLock


class Git(git.cmd.Git):
    """Prevents asking for password for private repos"""
    env = {'GIT_ASKPASS': 'echo'}

    def __getattr__(self, item):
        def wrapper(*args, **kwargs):
            env = kwargs.pop('env', {})
            env.update(self.env)
            return super(Git, self).__getattr__(item)(*args, env=env, **kwargs)

        return wrapper


class AsmProcessLock(InterProcessLock):
    def __init__(self):
        lock_path = join(gettempdir(), 'asm_lock')
        if not exists(lock_path):
            lock_file = open(lock_path, '+w')
            lock_file.close()
            chmod(lock_path, 0o777)
        super().__init__(lock_path)

class cached_property(object):
    """Decorator for read-only properties evaluated only once within TTL period.

    It can be used to create a cached property like this::

        import random

        # the class containing the property must be a new-style class
        class MyClass(object):
            # create property whose value is cached for ten minutes
            @cached_property(ttl=600)
            def randint(self):
                # will only be evaluated every 10 min. at maximum.
                return random.randint(0, 100)

    The value is cached  in the '_cache' attribute of the object instance that
    has the property getter method wrapped by this decorator. The '_cache'
    attribute value is a dictionary which has a key for every property of the
    object which is wrapped by this decorator. Each entry in the cache is
    created only when the property is accessed for the first time and is a
    two-element tuple with the last computed property value and the last time
    it was updated in seconds since the epoch.

    The default time-to-live (TTL) is 300 seconds (5 minutes). Set the TTL to
    zero for the cached value to never expire.

    To expire a cached property value manually just do::

        del instance._cache[<property name>]

    """

    def __init__(self, ttl=300):
        self.ttl = ttl

    def __call__(self, fget, doc=None):
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__
        self.__module__ = fget.__module__
        return self

    def __get__(self, inst, owner):
        now = time.monotonic()
        try:
            value, last_update = inst._cache[self.__name__]
            if self.ttl > 0 and now - last_update > self.ttl:
                raise AttributeError
        except (KeyError, AttributeError):
            value = self.fget(inst)
            try:
                cache = inst._cache
            except AttributeError:
                cache = inst._cache = {}
            cache[self.__name__] = (value, now)
        return value
