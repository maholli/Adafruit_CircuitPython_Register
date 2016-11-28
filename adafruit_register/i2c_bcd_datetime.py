try:
    import ucollections as collections
except:
    import collections

# TODO(tannewt): Split out the datetime tuple stuff so it can be shared more widely.
DateTimeTuple = collections.namedtuple("DateTimeTuple", ["year", "month",
    "day", "weekday", "hour", "minute", "second", "millisecond"])

def datetime_tuple(year, month, day, weekday=0, hour=0, minute=0,
                    second=0, millisecond=0):
    """Converts individual values into a `DateTimeTuple` with defaults.

    :param int year: The year
    :param int month: The month
    :param int day: The day
    :param int weekday: The day of the week (0-6)
    :param int hour: The hour
    :param int minute: The minute
    :param int second: The second
    :param int millisecond: not supported
    :return: The date and time
    :rtype: DateTimeTuple
    """
    return DateTimeTuple(year, month, day, weekday, hour, minute,second,
        millisecond)

def _bcd2bin(value):
    """Convert binary coded decimal to Binary

    Arguments:
    value - the BCD value to convert to binary (required, no default)
    """
    return value - 6 * (value >> 4)


def _bin2bcd(value):
    """Convert a binary value to binary coded decimal.

    Arguments:
    value - the binary value to convert to BCD. (required, no default)
    """
    return value + 6 * (value // 10)

class BCDDateTimeRegister:
    """
    Date and time register using binary coded decimal structure.

    The byte order of the register must be: second, minute, hour, weekday, day, month, year (in years after 2000).

    Values are `DateTimeTuple`

    :param int register_address: The register address to start the read
    """
    def __init__(self, register_address):
        self.buffer = bytearray(8)
        self.buffer[0] = register_address
        self.register_address = memoryview(self.buffer)[:1]
        self.datetime = memoryview(self.buffer)[1:]

    def __get__(self, obj, objtype=None):
        # Read and return the date and time.
        obj.i2c.writeto(obj.device_address, self.register_address, stop=False)
        obj.i2c.readfrom_into(obj.device_address, self.datetime)
        return datetime_tuple(
            year=_bcd2bin(self.datetime[6]) + 2000,
            month=_bcd2bin(self.datetime[5]),
            day=_bcd2bin(self.datetime[4]),
            weekday=_bcd2bin(self.datetime[3]),
            hour=_bcd2bin(self.datetime[2]),
            minute=_bcd2bin(self.datetime[1]),
            second=_bcd2bin(self.datetime[0]),
        )

    def __set__(self, obj, value):
        self.datetime[0] = _bin2bcd(value.second)   # format conversions
        self.datetime[1] = _bin2bcd(value.minute)
        self.datetime[2] = _bin2bcd(value.hour)
        self.datetime[3] = _bin2bcd(value.weekday)
        self.datetime[4] = _bin2bcd(value.day)
        self.datetime[5] = _bin2bcd(value.month)
        self.datetime[6] = _bin2bcd(value.year - 2000)
        obj.i2c.writeto(obj.device_address, self.buffer)

class BCDAlarmTimeRegister:
    """
    Date and time register using binary coded decimal structure.

    The byte order of the register must be: minute, hour, day, weekday.

    Values are `DateTimeTuple` with year, month and seconds ignored.

    :param int register_address: The register address to start the read
    """
    def __init__(self, register_address):
        self.buffer = bytearray(5)
        self.buffer[0] = register_address
        self.register_address = memoryview(self.buffer)[:1]
        self.alarm_time = memoryview(self.buffer)[1:]

    def __get__(self, obj, objtype=None):
        # Read the alarm register.
        obj.i2c.writeto(obj.device_address, self.register_address, stop=False)
        obj.i2c.readfrom_into(obj.device_address, self.alarm_time)
        if not self.alarm_time[0] & 0x80:
            return None
        return datetime_tuple(
            weekday=_bcd2bin(self.alarm_time[3] & 0x7f),
            day=_bcd2bin(self.alarm_time[2] & 0x7f),
            hour=_bcd2bin(self.alarm_time[1] & 0x7f),
            minute=_bcd2bin(self.alarm_time[0] & 0x7f),
        )

    def __set__(self, obj, value):
        self.alarm_time[1] = (_bin2bcd(value.minute) if value.minute is not None else 0x80)
        self.alarm_time[2] = (_bin2bcd(value.hour) if value.hour is not None else 0x80)
        self.alarm_time[3] = (_bin2bcd(value.day) if value.day is not None else 0x80)
        self.alarm_time[4] = (_bin2bcd(value.weekday) | 0b01000000 if value.weekday is not None else 0x80)
        obj.i2c.writeto(obj.device_address, self.buffer)
