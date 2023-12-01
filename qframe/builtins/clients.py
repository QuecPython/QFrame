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

import sms
from .. import AppExtensionABC
from ..threading import Condition, Thread, Queue
from ..datetime import DateTime, TimeDelta
from ..qsocket import TcpSocket
from ..logging import getLogger


logger = getLogger(__name__)


class TcpClient(AppExtensionABC):

    def __init__(self, name, app=None):
        self.__sock = None
        self.__listen_thread = Thread(target=self.__listen_thread_worker)
        self.__reconn_cond = Condition()
        self.__reconn_thread = Thread(target=self.__reconn_thread_worker)
        super().__init__(name, app=app)

    def __str__(self):
        return str(self.sock)

    def init_app(self, app):
        self.__sock = TcpSocket(**app.config['TCP_SERVER'])
        app.append_extension(self)

    def load(self):
        self.connect()

    @property
    def sock(self):
        if self.__sock is None:
            raise ValueError('client not init.')
        return self.__sock

    def recv_callback(self, data):
        raise NotImplementedError('you must implement this method to handle data received by tcp.')

    def __listen_thread_worker(self):
        while True:
            try:
                data = self.sock.read(1024)
            except self.sock.TimeoutError:
                # logger.debug('{} read timeout'.format(self))
                continue
            except Exception as e:
                logger.error('{} read error: {}'.format(self, e))
                with self.__reconn_cond:
                    self.__reconn_thread.start()
                    self.__reconn_cond.notify()
                break
            else:
                try:
                    self.recv_callback(data)
                except Exception as e:
                    logger.error('recv_callback error: {}'.format(e))

    def disconnect(self):
        logger.info('{} disconnect'.format(self))
        try:
            self.sock.disconnect()
            self.__listen_thread.stop()
        except Exception as e:
            logger.error('{} disconnect failed: {}'.format(self, e))
            return False
        return True

    def connect(self):
        logger.info('{} connecting...'.format(self))
        try:
            self.sock.connect()
        except Exception as e:
            logger.error('{} connect failed: {}'.format(self, e))
            return False
        self.__listen_thread.start()
        logger.info('{} connect successfully'.format(self))
        return True

    def __reconn_thread_worker(self):
        with self.__reconn_cond:
            self.disconnect()
            while not self.connect():
                last_reconn_time = DateTime.now()
                self.disconnect()
                self.__reconn_cond.wait_for(
                    lambda: DateTime.now() - last_reconn_time > TimeDelta(seconds=10),
                    timeout=60
                )

    def send(self, data):
        with self.__reconn_cond:
            try:
                return self.sock.write(data)
            except Exception as e:
                logger.error('cloud send error: {}; try to reconnect.'.format(e))
                self.__reconn_thread.start()
                self.__reconn_cond.notify()
                return False


class SmsClient(AppExtensionABC):

    def __init__(self, name, app=None):
        self.__queue = Queue()
        self.__recv_thread = Thread(target=self.__recv_thread_worker)
        super().__init__(name, app=app)

    def __getattr__(self, name):
        return getattr(sms, name)

    def init_app(self, app):
        app.append_extension(self)

    def __put(self, args):
        # args[0]	整型	当前SIM卡卡槽的simId
        # args[1]	整型	短信索引
        # args[2]	字符串 短信存储位置
        self.__queue.put(args)

    def __recv_thread_worker(self):
        while True:
            args = self.__queue.get()
            index = args[1]
            try:
                data = self.searchTextMsg(index)
                if data != -1:
                    self.recv_callback(*data)
                else:
                    logger.warn('got msg failed!')
            except Exception as e:
                logger.error('git msg error: {}'.format(e))
                continue

    def recv_callback(self, phone, msg, length):
        raise NotImplementedError

    def start(self):
        self.setCallback(self.__put)
        self.__recv_thread.start()
