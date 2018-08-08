from datetime import timedelta
from enum import Enum, unique
from typing import Any

import aiohttp

HEARTBEAT_INTERVAL = timedelta(seconds=2)

CLOSE_MESSAGES = (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSING,
                  aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR,)


class ByValue(Enum):
    @classmethod
    def by_value(cls, value: int) -> Any:
        for val in cls:
            if val.value == value:
                return val
        raise IndexError(value)


@unique
class ClientMessageType(ByValue):
    INBOX_MESSAGE = 1
    RPC_REQUEST = 2


@unique
class ServerMessageType(ByValue):
    MESSAGE = 1
    ERROR = 2
    BROADCAST = 3
    THROTTLING = 4


class ServerErrorType(ByValue):
    UNKNOWN_ERROR = -1
    DUPLICATE_CLIENT_ORDER_ID = 1
    INVALID_PAYLOAD = 2
