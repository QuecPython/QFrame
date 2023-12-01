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

from .threading import Lock


class ContextVar(object):
    """Context Variable"""
    __storage__ = {}
    __lock__ = Lock()

    def __init__(self, ident, error_msg=None):
        self.__ident = ident
        self.__error_msg = error_msg or '\"{}\" cannot be found in the current context'.format(self.ident)

    @property
    def ident(self):
        if callable(self.__ident):
            return self.__ident()
        return self.__ident

    def set(self, value):
        with self.__lock__:
            self.__storage__[self.ident] = value

    def get(self):
        with self.__lock__:
            if self.ident not in self.__storage__:
                raise RuntimeError(self.__error_msg)
            return self.__storage__[self.ident]

    def __call__(self, *args, **kwargs):
        return self.get()


class _AppCtxGlobals(object):

    def setdefault(self, name, value):
        if hasattr(self, name):
            return getattr(self, name)
        else:
            setattr(self, name, value)
            return value

    def get(self, name, default=None):
        if hasattr(self, name):
            return getattr(self, name)
        else:
            return default

    def set(self, name, value):
        setattr(self, name, value)


_no_app_msg = 'Working outside of application context.'
CurrentApp = ContextVar('Application', error_msg=_no_app_msg)
G = ContextVar('_AppCtxGlobals', error_msg=_no_app_msg)
