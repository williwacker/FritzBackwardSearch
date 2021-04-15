import logging

from fritzCallMon import CallMonServer

logger = logging.getLogger(__name__)


if __name__ == '__main__':
    CallMonServer().runServer()
