import re
import yaml
import aiofiles

from contextlib import suppress
from urllib.parse import unquote_plus


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
