
import logging
from python_log_indenter import IndentedLoggerAdapter as Logger


def getLogger(name):
    return Logger(logging.getLogger(name))

basicConfig = logging.basicConfig


CRITICAL = logging.CRITICAL
ERROR = logging.ERROR
WARNING = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG
NOTSET = logging.NOTSET
