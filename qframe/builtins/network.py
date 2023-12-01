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

import sim
import net
import utime
import checkNet
import dataCall
from misc import Power
from .. import AppExtensionABC
from ..logging import getLogger
from ..threading import Thread


logger = getLogger(__name__)


class NetWork(AppExtensionABC):

    def __init__(self, name, app=None):
        self.callback_handlers = {}
        super().__init__(name, app=app)

    def init_app(self, app):
        app.append_extension(self)

    def load(self):
        self.active_sim_hot_swap()
        self.active_net_callback()
        self.wait_network_ready()

    def active_sim_hot_swap(self):
        try:
            trigger_level = 0
            if sim.setSimDet(1, trigger_level) != 0:
                logger.warn('active sim switch failed.')
            else:
                logger.debug('active sim switch success.')
                if sim.setCallback(self.__sim_callback) != 0:
                    logger.warn('register sim switch callback failed.')
                else:
                    logger.debug('register sim switch callback success.')
        except Exception as e:
            logger.error('sim check init failed: {}'.format(e))
        else:
            logger.debug('sim check init success.')

    def active_net_callback(self):
        try:
            if dataCall.setCallback(self.__net_callback) != 0:
                logger.warn('register data callback failed.')
            else:
                logger.debug('register data callback success.')
        except Exception as e:
            logger.warn('net check init failed: {}'.format(e))
        else:
            logger.debug('net check init success.')

    @staticmethod
    def make_cfun():
        net.setModemFun(0, 0)
        utime.sleep_ms(200)
        net.setModemFun(1, 0)

    def wait_network_ready(self):
        total = 0
        while True:
            logger.info('wait network ready...')
            code = checkNet.waitNetworkReady(60)
            if code == (3, 1):
                logger.info('network has been ready.')
                break
            else:
                logger.warn('network not ready, code: {}'.format(code))
                if 3 <= total < 6:
                    logger.warn('make cfun switch.')
                    self.make_cfun()
                if total >= 6:
                    logger.warn('power restart.')
                    Power.powerRestart()
            total += 1

    def __net_callback(self, args):
        # WARN: Do not write time-consuming or blocking code here
        logger.info('net_callback get args: {}'.format(args))
        handlers = self.callback_handlers.setdefault('net', [])
        for handler in handlers:
            Thread(target=handler, args=(args,)).start()
        if args[1] == 0:
            Thread(target=self.wait_network_ready).start()

    def register_net_callback(self, fn):
        handlers = self.callback_handlers.setdefault('net', [])
        handlers.append(fn)
        return fn

    def __sim_callback(self, state):
        # WARN: Do not write time-consuming or blocking code here
        logger.info('sim_callback get state: {}'.format(state))
        handlers = self.callback_handlers.setdefault('sim', [])
        for handler in handlers:
            Thread(target=handler, args=(state,)).start()

    def register_sim_callback(self, fn):
        handlers = self.callback_handlers.setdefault('sim', [])
        handlers.append(fn)
        return fn


network = NetWork('network')
