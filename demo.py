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

import checkNet
from usr.qframe import Application, CurrentApp
from usr.qframe import TcpClient, Uart
from usr.qframe.logging import getLogger


logger = getLogger(__name__)


PROJECT_NAME = 'Sample DTU'
PROJECT_VERSION = '1.0.0'


def poweron_print_once():
    checknet = checkNet.CheckNetwork(
        PROJECT_NAME,
        PROJECT_VERSION,
    )
    checknet.poweron_print_once()


class BusinessClient(TcpClient):

    def recv_callback(self, data):
        """implement this method to handle data received from tcp server

        :param data: data bytes received from tcp server
        :return:
        """
        logger.info('recv data from tcp server, then post to uart')
        CurrentApp().uart.write(data)


class UartService(Uart):

    def recv_callback(self, data):
        """implement this method to handle data received from UART

        :param data: data bytes received from UART
        :return:
        """
        logger.info('read data from uart, then post to tcp server')
        CurrentApp().client.send(data)


def create_app(name='DTU', config_path='/usr/dev.json'):
    # init application
    _app = Application(name)
    # read settings from json file
    _app.config.from_json(config_path)

    # init business tcp client
    client = BusinessClient('client')
    client.init_app(_app)

    # init business uart
    uart = UartService('uart')
    uart.init_app(_app)

    return _app


app = create_app()


if __name__ == '__main__':
    poweron_print_once()
    app.mainloop()
