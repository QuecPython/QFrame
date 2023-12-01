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

import uos
import uzlib
import ql_fs
import request
import fota as BaseFota
import app_fota as BaseAppFota
from app_fota_download import update_download_stat
from .threading import Event


class Fota(object):

    def __init__(self, auto_reset=False, progress_callback=None):
        """OTA升级。

        @auto_reset: True表示下载成功自动重启，False表示不自动重启。
        @progress_callback: 升级包下载进度的回调函数，传入唯一位置参数是一个整数(0~100)表示进度百分比。
        """
        self.fota = BaseFota(reset_disable=int(not auto_reset))
        self.__finished = Event()
        self.__success = False
        self.__progress_callback = progress_callback

    def __download_callback(self, args):
        if args[0] in (0, 1, 2):
            if self.__progress_callback:
                self.__progress_callback(args[1])
            if args[1] == 100:
                self.__success = True
                self.__finished.set()
        else:
            self.__success = False
            self.__finished.set()

    def get_result(self, timeout=None):
        """获取差分升级包下载的异步结果。

        @timeout: 超时时间(s)。
        @return: True表示成功，False表示失败。
        """
        self.__finished.wait(timeout=timeout)
        return self.__success

    def upgrade(self, url):
        """差分升级模式。

        @url: 升级包下载链接（HTTP或FTP，仅EC200A型号支持FTP）。
        @return: EC600N/EC800N/EG912N/EC600M/EC800M/EG810M/BC25PA型号，返回值只代表接口执行成功或失败，
        升级状态和结果需通过`get_result()`反馈。其他型号返回True表示下载和校验成功，返回False表示下载或校验失败。
        """
        self.__finished.clear()
        self.__success = False
        return self.fota.httpDownload(url1=url, callback=self.__download_callback) == 0

    def mini_upgrade(self, url1, url2):
        """最小系统升级。仅EC600N/EC800N/EG912N/EC600M/EC800M/EG810M型号支持改方式。

        @url1: 第一阶段升级包下载链接。
        @url2: 第二阶段升级包下载链接。
        @return: 返回True表示下载和校验成功，返回False表示下载或校验失败。
        """
        return self.fota.httpDownload(url1=url1, url2=url2) == 0

    def local_upgrade(self, path):
        """
        本地升级。

        @path: 升级固件包本地文件路径。
        @return: (result, code), result是布尔值True表示成功，False表示失败；code是错误码，1表示升级包数据流写入失败，2表示刷新RAM缓存
        数据到flash失败，3表示校验失败。
        """
        with open(path, 'rb') as f:
            size = f.seek(0, 2)
            f.seek(0, 0)
            while True:
                content = f.read(4096)
                if not content:
                    break
                if self.fota.write(content, size) == -1:
                    return False, 1
                if self.__progress_callback:
                    self.__progress_callback(int(f.tell() / size * 100))
        if self.fota.flush() == -1:
            return False, 2
        if self.fota.verify() == -1:
            return False, 3
        return True, 0


class FileDecode(object):

    def __init__(self, zip_file, parent_dir="/fota/usr/"):
        self.data = b''
        self.fp = open(zip_file, "rb")
        self.fileData = None
        self.parent_dir = parent_dir
        self.update_file_list = []

    def get_update_files(self):
        return self.update_file_list

    def unzip(self):
        """缓存到内存中"""
        self.fp.seek(10)
        self.fileData = uzlib.DecompIO(self.fp, -15, 1)

    @classmethod
    def _ascii_trip(cls, data):
        return data.decode('ascii').rstrip('\0')

    @classmethod
    def file_size(cls, data):
        """获取真实size数据"""
        size = cls._ascii_trip(data)
        if not len(size):
            return 0
        return int(size, 8)

    @classmethod
    def get_file_name(cls, file_name):
        """获取文件名称"""
        return cls._ascii_trip(file_name)

    def get_data(self):
        return self.fileData.read(0x200)

    def unpack(self):
        try:
            folder_list = set()
            self.data = self.get_data()
            while True:
                if not self.data:
                    break
                size = self.file_size(self.data[124:135])
                file_name = self.get_file_name(self.data[:100])
                full_file_name = self.parent_dir + file_name

                if not size:
                    if len(full_file_name):
                        ql_fs.mkdirs(full_file_name)
                        if full_file_name not in folder_list and full_file_name != self.parent_dir:
                            folder_list.add(full_file_name)
                    else:
                        return
                    self.data = self.get_data()
                else:
                    self.data = self.get_data()
                    update_file = open(full_file_name, "wb+")
                    total_size = size
                    while True:
                        size -= 0x200
                        if size <= 0:
                            update_file.write(self.data[:size + 512])
                            break
                        else:
                            update_file.write(self.data)
                        self.data = self.get_data()
                    self.data = self.get_data()
                    update_file.close()
                    self.update_file_list.append({"file_name": file_name, "size": total_size})
        except Exception as e:
            self.fp.close()
            return False
        else:
            self.fp.close()
            return True


class AppFota(object):

    def __init__(self):
        self.fota = BaseAppFota.new()

    def set_update_flag(self):
        """设置升级标志（当且仅当升级文件下载成功后，且设置了升级标志，重启后才会触发升级，否则不升级。）"""
        self.fota.set_update_flag()

    def download(self, url, file_name):
        """下载单一升级文件

        @url: 待下载文件的url，类型为str。
        @file_name: 本地待升级文件的绝对路径，类型str。
        """
        if self.fota.download(url, file_name) == 0:
            return True
        return False

    def bulk_download(self, info):
        """批量下载升级文件

        @info: 批量下载列表，列表的元素均为包含了url和file_name的字典，类型为list
        """
        return self.fota.bulk_download(info)

    @staticmethod
    def __download_file_from_server(url, path):
        response = request.get(url)
        if response.status_code not in (200, 206):
            return False
        with open(path, 'wb') as f:
            for c in response.content:
                f.write(c)

    @staticmethod
    def __decode_file_to_updater_dir(path, updater_dir):
        fd = FileDecode(path, parent_dir=updater_dir)
        ql_fs.mkdirs(updater_dir)
        fd.unzip()
        if fd.unpack():
            for file in fd.update_file_list:
                update_download_stat('', '/usr/' + file['file_name'], file['size'])
            return True
        else:
            return False

    def download_tar(self, url, path="/usr/temp.tar.gz"):
        """通过压缩文件下载升级。"""
        self.__download_file_from_server(url, path)
        if self.__decode_file_to_updater_dir(
            path,
            self.fota.app_fota_pkg_mount.fota_dir + '/usr/.updater/usr/'
        ):
            uos.remove(path)
            return True
        else:
            return False
