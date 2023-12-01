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

from .. import AppExtensionABC
from ..threading import Thread
from ..serial import Serial as _Serial
from ..logging import getLogger

logger = getLogger(__name__)


class Uart(AppExtensionABC):

    def __init__(self, name, app=None):
        self.serial = None
        self.write = None
        self.read = None
        self.listen_thread = None
        super().__init__(name, app=app)

    def init_app(self, app):
        self.serial = _Serial(**app.config['UART'])
        self.write = self.serial.write
        self.read = self.serial.read
        self.listen_thread = Thread(target=self.listen_thread_worker)
        app.append_extension(self)

    def load(self):
        self.serial.open()
        self.listen_thread.start()

    def listen_thread_worker(self):
        while True:
            try:
                data = self.read(1024)
            except Exception as e:
                logger.error('serial read error: {}'.format(e))
            else:
                try:
                    self.recv_callback(data)
                except Exception as e:
                    logger.error('recv_callback error: {}'.format(e))

    def recv_callback(self, data):
        raise NotImplementedError('you must implement this method to handle data received from device.')
