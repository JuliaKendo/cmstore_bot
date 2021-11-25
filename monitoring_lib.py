from __future__ import annotations

import asks
import functools

from environs import Env
from contextlib import suppress
from datetime import datetime

env = Env()
env.read_env()

monitoring_url = env.str('MONITORING_SERVER')


def prepare_params(message, status):
    return {
        'date': datetime.now().timestamp(),
        'session': 'cmstore_krd_bot',
        'chat_id': message['chat']['id'],
        'message_id': message['message_id'],
        'status': status,
        'message': message['text']
    }


async def request_data(status, *message_seq):
    with suppress(Exception):  # Гарантирует выполнение остального кода, вне зависимости от мониторинга
        message = message_seq[0]
        params = prepare_params(message, status)
        response = await asks.post(
            monitoring_url, json=params
        )
        response.raise_for_status()


def handle_monitoring_log():
    def decorator(func):
        @functools.wraps(func)
        async def inner(*args, **kwargs):
            await request_data('send confirmation to client', *args)
            message_seq = await func(*args, **kwargs)
            if not isinstance(message_seq, list):
                await request_data('send result to client', *[message_seq])
            else:
                await request_data('send result to client', *message_seq)
            return message_seq
        return inner
    return decorator
