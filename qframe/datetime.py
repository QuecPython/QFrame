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


class UtimeAdapter(object):
    """QuecPython platform `utime` module adapter"""

    @staticmethod
    def get_local_time_tuple():
        return utime.localtime()

    @staticmethod
    def get_timestamp_from_time_tuple(time_tuple):
        return utime.mktime(time_tuple)

    @staticmethod
    def get_time_tuple_from_timestamp(timestamp):
        return utime.localtime(timestamp)

    @staticmethod
    def get_local_timezone_offset():
        return utime.getTimeZone()

    @staticmethod
    def set_local_timezone_offset(offset):
        return utime.setTimeZone(offset) == 0


class TimeZone(object):

    def __init__(self, offset=0, name='N/A'):
        self.__offset = self.__validate_offset(offset)
        self.__name = name

    def __str__(self):
        return 'UTC{:+02d}:00'.format(self.offset)

    @staticmethod
    def __validate_offset(offset):
        if not (isinstance(offset, int) and -12 <= offset <= 12):
            raise ValueError('offset should be int type and between [-12, 12].')
        return offset

    @property
    def offset(self):
        return self.__offset

    @property
    def name(self):
        return self.__name


UTC = TimeZone(offset=0, name='UTC')


class TimeDelta(object):

    def __init__(self, days=0, seconds=0, hours=0, minutes=0, weeks=0):
        seconds += (minutes * 60 + (hours % 24 * 3600))
        self.__seconds = seconds % 86400
        self.__days = days + weeks * 7 + hours // 24 + seconds // 86400

    def __str__(self):
        return '{} days, {} seconds'.format(self.days, self.seconds)

    def __add__(self, other):
        if isinstance(other, type(self)):
            return type(self)(
                days=self.days + other.days,
                seconds=self.seconds + other.seconds
            )
        elif isinstance(other, DateTime):
            return other + self
        else:
            raise TypeError("unsupported operand type(s) for +: '{}' and '{}'".format(type(self), type(other)))

    def __sub__(self, other):
        if isinstance(other, type(self)):
            return type(self)(
                days=self.days - other.days,
                seconds=self.seconds - other.seconds
            )
        else:
            raise TypeError("unsupported operand type(s) for -: '{}' and '{}'".format(type(self), type(other)))

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("unsupported operand type(s) for <: '{}' and '{}'".format(type(self), type(other)))
        return (self - other).total_seconds() < 0

    def __le__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("unsupported operand type(s) for <=: '{}' and '{}'".format(type(self), type(other)))
        return (self - other).total_seconds() <= 0

    def __gt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("unsupported operand type(s) for >: '{}' and '{}'".format(type(self), type(other)))
        return (self - other).total_seconds() > 0

    def __ge__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("unsupported operand type(s) for >=: '{}' and '{}'".format(type(self), type(other)))
        return (self - other).total_seconds() >= 0

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("unsupported operand type(s) for ==: '{}' and '{}'".format(type(self), type(other)))
        return (self - other).total_seconds() == 0

    def __ne__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("unsupported operand type(s) for !=: '{}' and '{}'".format(type(self), type(other)))
        return (self - other).total_seconds() != 0

    @property
    def days(self):
        return self.__days

    @property
    def seconds(self):
        return self.__seconds

    def total_seconds(self):
        return self.days * 86400 + self.seconds


def is_leap_year(year):
    return not year % 4 if year % 100 else not year % 400


class _Date(object):

    def __init__(self, year, month=1, day=1):
        self.__year = year
        self.__month = month
        self.__day = day
        self.__validate()

    def __str__(self):
        return '{:04d}-{:02d}-{:02d}'.format(self.year, self.month, self.day)

    def __is_day_valid(self):
        if self.__month == 2:
            return 1 <= self.__day <= 29 if is_leap_year(self.__year) else 1 <= self.__day <= 28
        else:
            return 1 <= self.__month <= 31 if self.__month in [1, 3, 5, 7, 8, 10, 12] else 1 <= self.__month <= 30

    def __validate(self):
        if not (isinstance(self.__year, int) and 1 <= self.__year <= 9999):
            raise ValueError('\"year\" is not valid.')
        if not (isinstance(self.__month, int) and 1 <= self.__month <= 12):
            raise ValueError('\"month\" is not valid.')
        if not (isinstance(self.__day, int) and self.__is_day_valid()):
            raise ValueError('\"day\" is not valid.')

    @property
    def year(self):
        return self.__year

    @property
    def month(self):
        return self.__month

    @property
    def day(self):
        return self.__day


class _Time(object):

    def __init__(self, hour=0, minute=0, second=0):
        self.__hour = hour
        self.__minute = minute
        self.__second = second
        self.__validate()

    def __str__(self):
        return '{:02d}:{:02d}:{:02d}'.format(self.hour, self.minute, self.second)

    def __validate(self):
        if not (isinstance(self.__hour, int) and 0 <= self.__hour <= 23):
            raise ValueError('\"hour\" is not valid.')
        if not (isinstance(self.__minute, int) and 0 <= self.__minute <= 59):
            raise ValueError('\"minute\" is not valid.')
        if not (isinstance(self.__second, int) and 0 <= self.__second <= 59):
            raise ValueError('\"second\" is not valid.')

    @property
    def hour(self):
        return self.__hour

    @property
    def minute(self):
        return self.__minute

    @property
    def second(self):
        return self.__second


class DateTime(object):

    def __init__(self, year, month=1, day=1, hour=0, minute=0, second=0, tz=None):
        self.__date = _Date(year, month, day)
        self.__time = _Time(hour, minute, second)
        self.__tz = tz
        self.__weekday = None
        self.__yearday = None

    def __str__(self):
        return '{} {}'.format(self.date, self.time) + (' {}'.format(self.tz) if self.tz else '')

    @property
    def year(self):
        return self.date.year

    @property
    def month(self):
        return self.date.month

    @property
    def day(self):
        return self.date.day

    @property
    def hour(self):
        return self.time.hour

    @property
    def minute(self):
        return self.time.minute

    @property
    def second(self):
        return self.time.second

    @property
    def date(self):
        return self.__date

    @property
    def time(self):
        return self.__time

    @property
    def tz(self):
        return self.__tz

    def __calc_year_and_week_day(self):
        days = 0
        for m in range(1, self.month):
            if m == 2:
                days += (29 if is_leap_year(self.year) else 28)
            else:
                days += (31 if m in [1, 3, 5, 7, 8, 10, 12] else 30)
        self.__yearday = days + self.day
        year = self.year - 1
        self.__weekday = (year + year // 4 - year // 100 + year // 400 + self.__yearday) % 7

    @property
    def weekday(self):
        if self.__weekday is None:
            self.__calc_year_and_week_day()
        return self.__weekday

    @property
    def yearday(self):
        if self.__yearday is None:
            self.__calc_year_and_week_day()
        return self.__yearday

    @property
    def timetuple(self):
        return self.year, self.month, self.day, self.hour, self.minute, self.second, self.weekday, self.yearday

    @property
    def timestamp(self):
        __timestamp__ = getattr(self, '__timestamp__', None)
        if __timestamp__ is None:
            __timestamp__ = UtimeAdapter.get_timestamp_from_time_tuple(self.timetuple)
        return __timestamp__

    @classmethod
    def fromtimestamp(cls, timestamp, tz=None):
        time_tuple = UtimeAdapter.get_time_tuple_from_timestamp(timestamp)
        return cls(*time_tuple[:6], tz=tz)

    @classmethod
    def utcnow(cls):
        return cls.now(tz=UTC)

    @classmethod
    def now(cls, tz=None):
        if not isinstance(tz, (TimeZone, type(None))):
            raise TypeError('\"tz\" should be TimeZone type or None.')
        time_tuple = UtimeAdapter.get_local_time_tuple()
        self = cls(
            *time_tuple[:6],
            tz=TimeZone(offset=UtimeAdapter.get_local_timezone_offset())
        )
        if tz:
            self = self.astimezone(tz)
        return self

    def replace(self, year=None, month=None, day=None, hour=None,
                minute=None, second=None, tz=None):
        if year is None:
            year = self.year
        if month is None:
            month = self.month
        if day is None:
            day = self.day
        if hour is None:
            hour = self.hour
        if minute is None:
            minute = self.minute
        if second is None:
            second = self.second
        if tz is None:
            tz = self.tz
        return type(self)(year, month, day, hour, minute, second, tz=tz)

    def astimezone(self, tz=None):
        if not (isinstance(tz, TimeZone) and isinstance(self.tz, TimeZone)):
            raise TypeError('can not convert without timezone information.')
        utctime = (self - TimeDelta(hours=self.tz.offset)).replace(tz=UTC)
        return (utctime + TimeDelta(hours=tz.offset)).replace(tz=tz)

    def __sub__(self, other):
        if isinstance(other, TimeDelta):
            time_tuple = UtimeAdapter.get_time_tuple_from_timestamp(self.timestamp - other.total_seconds())
            return type(self)(
                *time_tuple[:6],
                tz=self.tz
            )
        elif isinstance(other, type(self)):
            seconds = self.timestamp - other.timestamp
            if all((self.tz, other.tz)):
                seconds -= (self.tz.offset - other.tz.offset) * 3600
            return TimeDelta(seconds=seconds)
        else:
            raise TypeError("unsupported operand type(s) for -: '{}' and '{}'".format(type(self), type(other)))

    def __add__(self, other):
        if isinstance(other, TimeDelta):
            time_tuple = UtimeAdapter.get_time_tuple_from_timestamp(self.timestamp + other.total_seconds())
            return type(self)(*time_tuple[:6], tz=self.tz)
        else:
            raise TypeError("unsupported operand type(s) for +: '{}' and '{}'".format(type(self), type(other)))

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("unsupported operand type(s) for <: '{}' and '{}'".format(type(self), type(other)))
        return (self - other).total_seconds() < 0

    def __le__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("unsupported operand type(s) for <=: '{}' and '{}'".format(type(self), type(other)))
        return (self - other).total_seconds() <= 0

    def __gt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("unsupported operand type(s) for >: '{}' and '{}'".format(type(self), type(other)))
        return (self - other).total_seconds() > 0

    def __ge__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("unsupported operand type(s) for >=: '{}' and '{}'".format(type(self), type(other)))
        return (self - other).total_seconds() >= 0

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("unsupported operand type(s) for ==: '{}' and '{}'".format(type(self), type(other)))
        return (self - other).total_seconds() == 0

    def __ne__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("unsupported operand type(s) for !=: '{}' and '{}'".format(type(self), type(other)))
        return (self - other).total_seconds() != 0
