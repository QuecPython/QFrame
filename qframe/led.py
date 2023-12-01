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
from machine import Pin
from .threading import Thread, Semaphore, Lock


class Led(object):

    def __init__(self, GPIOn):
        self.__led = Pin(
            getattr(Pin, 'GPIO{}'.format(GPIOn)),
            Pin.OUT,
            Pin.PULL_PD,
            0
        )
        self.__off_remaining = 1000
        self.__on_remaining = 1000
        self.__running_sem = Semaphore(value=0)
        self.__blink_lock = Lock()
        self.__blink_thread = Thread(target=self.__blink_thread_worker)

    def on(self):
        self.__led.write(1)

    def off(self):
        self.__led.write(0)

    def blink(self, on_remaining, off_remaining, count):
        """start LED blink"""
        with self.__blink_lock:
            self.__on_remaining = on_remaining
            self.__off_remaining = off_remaining
            self.__blink_thread.start()
        self.__running_sem.clear()
        self.__running_sem.release(count)

    def __blink_thread_worker(self):
        while True:
            self.__running_sem.acquire()
            with self.__blink_lock:
                on_remaining = self.__on_remaining
                off_remaining = self.__off_remaining
            self.on()
            utime.sleep_ms(on_remaining)
            self.off()
            utime.sleep_ms(off_remaining)
