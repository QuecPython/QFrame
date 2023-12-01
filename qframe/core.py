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

from .globals import CurrentApp, G, _AppCtxGlobals
from .collections import OrderedDict, LocalStorage
from .threading import ThreadPoolExecutor, Lock


class Application(object):
    """Application Class"""

    def __init__(self, name):
        self.name = name
        self.config = LocalStorage()
        self.business_threads_pool = ThreadPoolExecutor(max_workers=4, enable_priority=True)
        self.submit = self.business_threads_pool.submit
        # init builtins dictionary and init common, we use OrderedDict to keep loading ordering
        self.extensions = OrderedDict()
        self.__append_builtin_extensions()
        # set global context variable
        CurrentApp.set(self)
        G.set(_AppCtxGlobals())

    def __getattr__(self, item):
        return self.extensions[item]

    def __append_builtin_extensions(self):
        """add builtin builtins"""
        from .builtins import network
        network.init_app(self)

    def append_extension(self, extension):
        self.extensions[extension.name] = extension

    def mainloop(self):
        """load builtins"""
        for extension in self.extensions.values():
            if hasattr(extension, 'load'):
                extension.load()


class AppExtensionABC(object):
    """Abstract Application Extension Class"""

    def __init__(self, name, app=None):
        self.name = name
        if app:
            self.init_app(app)

    def init_app(self, app):
        # 将当前拓展对象注册进app中
        app.append_extesion(self)
        # 初始化应用拓展（读取配置）
        raise NotImplementedError

    def load(self):
        # 加载应用拓展相关功能，此接口会在app.mainloop中按照拓展初始化顺序调用。
        raise NotImplementedError
