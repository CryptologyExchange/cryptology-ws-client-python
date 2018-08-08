import aiohttp
import asyncio
import json
import logging

from . import exceptions, common
from datetime import datetime
from decimal import Decimal
from typing import Optional, Callable, Awaitable

__all__ = ('run',)

logger = logging.getLogger(__name__)


async def receive_msg(ws: aiohttp.ClientWebSocketResponse, *, timeout: Optional[float] = None) -> dict:
    msg = await ws.receive(timeout=timeout)
    if msg.type in common.CLOSE_MESSAGES:
        logger.info('close msg received (type %s): %s', msg.type.name, msg.data)
        exceptions.handle_close_message(msg)
        raise exceptions.UnsupportedMessage(msg)

    return json.loads(msg.data)


MarketDataCallback = Callable[[dict], Awaitable[None]]
OrderBookCallback = Callable[[int, str, dict, dict], Awaitable[None]]
TradesCallback = Callable[[datetime, int, str, Decimal, Decimal], Awaitable[None]]


async def reader_loop(
        ws: aiohttp.ClientWebSocketResponse,
        market_data_callback: MarketDataCallback,
        order_book_callback: OrderBookCallback,
        trades_callback: TradesCallback) -> None:
    logger.info(f'broadcast connection established')
    while True:
        msg = await receive_msg(ws)

        try:
            message_type: common.ServerMessageType = common.ServerMessageType[msg['response_type']]
            if message_type != common.ServerMessageType.BROADCAST:
                raise exceptions.UnsupportedMessageType()
            payload = msg['data']
            if market_data_callback is not None:
                await market_data_callback(payload)
            if payload['@type'] == 'OrderBookAgg':
                if order_book_callback is not None:
                    asyncio.ensure_future(order_book_callback(
                        payload['current_order_id'],
                        payload['trade_pair'],
                        payload.get('buy_levels', dict),
                        payload.get('sell_levels', dict)
                    ))
            elif payload['@type'] == 'AnonymousTrade':
                if trades_callback is not None:
                    asyncio.ensure_future(trades_callback(
                        datetime.utcfromtimestamp(payload['time'][0]),
                        payload['current_order_id'],
                        payload['trade_pair'],
                        Decimal(payload['amount']),
                        Decimal(payload['price'])
                    ))
            else:
                raise exceptions.UnsupportedMessageType()
        except (KeyError, ValueError, exceptions.UnsupportedMessageType):
            logger.exception('failed to decode data')
            raise exceptions.CryptologyError('failed to decode data')


async def run(*, ws_addr: str, market_data_callback: MarketDataCallback = None,
              order_book_callback: OrderBookCallback = None,
              trades_callback: TradesCallback = None,
              loop: Optional[asyncio.AbstractEventLoop] = Awaitable[None]) -> None:
    async with aiohttp.ClientSession(loop=loop) as session:
        async with session.ws_connect(ws_addr, receive_timeout=20, heartbeat=3) as ws:
            await reader_loop(ws, market_data_callback, order_book_callback, trades_callback)
