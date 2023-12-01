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

import ql_fs
import _thread


class Singleton(object):
    def __init__(self, cls):
        self.cls = cls
        self.instance = None

    def __call__(self, *args, **kwargs):
        if self.instance is None:
            self.instance = self.cls(*args, **kwargs)
        return self.instance

    def __repr__(self):
        return repr(self.cls)


class _Link(object):
    __slots__ = ('prev', 'next', 'key')


class OrderedDict(object):

    def __init__(self, sequence=None):
        self.root = _Link()
        self.map = {}
        self._node_map = {}
        self.root.next = self.root
        self.root.prev = self.root
        if sequence is not None:
            self.init(sequence)

    def init(self, sequence):
        for k, v in sequence:
            self[k] = v

    def __repr__(self):
        return repr([(key, self.map[key]) for key in self])

    def __setitem__(self, key, value):
        if key in self._node_map:
            self.map[key] = value
        else:
            root = self.root
            last = root.prev
            link = _Link()
            link.prev, link.next, link.key = last, root, key
            last.next = link
            root.prev = link
            self._node_map[key] = link
            self.map[key] = value

    def __getitem__(self, item):
        return self.map[item]

    def __delitem__(self, key):
        del self.map[key]
        link = self._node_map.pop(key)
        link_prev, link_next = link.prev, link.next
        link_prev.next, link_next.prev = link_next, link_prev
        link.prev, link.next = None, None

    def __iter__(self):
        root = self.root
        curr = root.next
        while curr != root:
            yield curr.key
            curr = curr.next

    def pop(self, key, default=None):
        if key not in self:
            return default
        temp = self[key]
        del self[key]
        return temp

    def keys(self):
        return iter(self)

    def values(self):
        return (self.map[k] for k in self)

    def items(self):
        return ((k, self.map[k]) for k in self)

    def setdefault(self, key, value):
        if key in self:
            return self[key]
        else:
            self[key] = value
            return value

    def update(self, obj):
        for k, v in obj.items():
            self[k] = v


def deepcopy(obj):
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    if isinstance(obj, (list, tuple)):
        return type(obj)([deepcopy(item) for item in obj])
    elif isinstance(obj, dict):
        return {k: deepcopy(v) for k, v in obj.items()}
    else:
        raise TypeError('unsupported for \"{}\" type'.format(type(obj)))


class LocalStorage(object):

    def __init__(self):
        self.__path = None
        self.__db = {}
        self.__lock = _thread.allocate_lock()

    def from_json(self, path):
        with self.__lock:
            self.__path = path
            if not ql_fs.path_exists(path):
                raise ValueError('\"{}\" not exists!'.format(path))
            self.__db.update(ql_fs.read_json(path))

    def save(self, to_path=None):
        with self.__lock:
            to_path = to_path or self.__path
            if to_path is None:
                raise ValueError('no path to save.')
            ql_fs.touch(to_path, self.__db)

    def update(self, *args, **kwargs):
        with self.__lock:
            self.__db.update(*args, **kwargs)
        return self

    def get(self, key, default=None):
        with self.__lock:
            return deepcopy(self.__db.get(key, default))

    def __getitem__(self, key):
        with self.__lock:
            return deepcopy(self.__db[key])

    def __setitem__(self, key, value):
        with self.__lock:
            self.__db[key] = value
        return self
