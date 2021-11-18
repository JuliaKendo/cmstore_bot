import asks
import re
import yaml
import aiofiles
import fake_useragent

from contextlib import suppress
from urllib.parse import unquote_plus


class RequestError(Exception):

    def __init__(self, error_message):
        self.message = error_message
        super().__init__(self.message)

    def __str__(self):
        return self.message


async def decode_message(message, template):
    decoded_message = message.decode('unicode_escape')
    text_messages = re.findall(template, decoded_message)
    return ''.join([unquote_plus(message) for message in text_messages])


async def read_file(path_to_file):
    with suppress(FileNotFoundError, TypeError):
        async with aiofiles.open(path_to_file, mode='rb') as f:
            content = await f.read()
        return content


async def save_file(path_to_file, content):
    with suppress(FileNotFoundError, TypeError):
        async with aiofiles.open(path_to_file, mode='wb') as f:
            f.write(content)


async def update_config(**params):
    settings = {}

    with suppress(FileNotFoundError, yaml.YAMLError, TypeError):
        async with aiofiles.open('config.yaml', mode='r') as f:
            content = await f.read()
            if not content:
                raise yaml.YAMLError
            settings = yaml.safe_load(content)

    settings.update(params)
    async with aiofiles.open('config.yaml', mode='w') as f:
        await f.write(str(settings))


async def read_config(param=''):
    with suppress(FileNotFoundError, yaml.YAMLError, TypeError):
        async with aiofiles.open('config.yaml', mode='r') as f:
            content = await f.read()
            if not content:
                raise yaml.YAMLError
        settings = yaml.safe_load(content)
        if not param:
            return settings
        return settings.get(param, None)


async def request_data(url, header, params):
    with suppress(asks.errors.BadStatus):
        responce = await asks.get(url, headers=header, params=params)
        responce.raise_for_status()
        reply = responce.json()
        if not reply.get('error'):
            return reply

    raise RequestError(responce.text)


async def is_valid_insta_account(insta_name):
    with suppress(KeyError, ValueError, TypeError, RequestError, AssertionError):
        _, nickname = re.split(r'^@', insta_name)
        if not nickname:
            return None
        user = fake_useragent.UserAgent().random
        response = await request_data(
            f'https://www.instagram.com/{nickname}',
            {'user-agent': user},
            {'__a': 1}
        )
        assert nickname == response['graphql']['user']['username']
        return True
