import os
import re
import glob
import asks
import yaml
import time
import config
import aiofiles
import functools

from contextlib import suppress
from instabot import Bot
from urllib.parse import unquote_plus
from pathlib import Path
from multiprocessing.pool import ThreadPool as Pool

from custom_exceptions import (
    RequestError,
    DocumentNotFound,
    NoActiveDrawFound,
    DocumentDoesNotMatch
)


def timeout(max_timeout):
    def decorator(func):
        @functools.wraps(func)
        def inner(*args):
            pool = Pool(processes=1)
            async_result = pool.apply_async(func, args)
            return async_result.get(max_timeout)
        return inner
    return decorator


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
        async with aiofiles.open(Path(config.PROJECT_ROOT, 'config.yaml'), mode='r') as f:
            content = await f.read()
            if not content:
                raise yaml.YAMLError
            settings = yaml.safe_load(content)

    settings.update(params)
    async with aiofiles.open(Path(config.PROJECT_ROOT, 'config.yaml'), mode='w') as f:
        await f.write(str(settings))


async def read_config(param=''):
    with suppress(FileNotFoundError, yaml.YAMLError, TypeError):
        async with aiofiles.open(Path(config.PROJECT_ROOT, 'config.yaml'), mode='r') as f:
            content = await f.read()
            if not content:
                raise yaml.YAMLError
        settings = yaml.safe_load(content)
        if param:
            return settings.get(param, None)
        return settings


async def request_data(url, header, params):
    with suppress(asks.errors.BadStatus):
        response = await asks.get(url, headers=header, params=params)
        response.raise_for_status()
        reply = response.json()
        if not reply.get('error'):
            return reply

    raise RequestError(response.text)


@timeout(30)
def init_insta_bot(login, password):
    print('init_insta_bot')
    cookie_del = glob.glob("config/*cookie.json")
    if cookie_del:
        os.remove(cookie_del[0])

    insta_bot = Bot()
    insta_bot.login(username=login, password=password)
    return insta_bot


async def is_valid_insta_account(insta_name, insta_bot=None):
    with suppress(ValueError, IndexError, asks.errors.BadStatus):
        parts_of_insta_name = re.split(r'^@', insta_name)
        nickname = parts_of_insta_name[-1]
        if insta_bot:
            return insta_bot.get_user_id_from_username(nickname)
        valid_insta_account = await is_valid_insta_account_without_login(nickname)
        return valid_insta_account


async def is_valid_insta_account_without_login(nickname):
    response = await asks.get(
        f'https://www.instagram.com/web/search/topsearch/?query={nickname}'
    )
    response.raise_for_status()
    reply = response.json()
    return [item for item in reply['users'] if item['user']['username'] == nickname]


async def get_document_identifiers_from_service(url, document_number):
    response = await asks.post(url, json={"documentNumber": document_number})
    response.raise_for_status()

    document_ids = response.json()
    if document_ids['document'] == 'not found':
        raise DocumentNotFound
    if document_ids['document'] == 'no active draw found':
        raise NoActiveDrawFound
    if document_ids['document'] == 'does not match':
        raise DocumentDoesNotMatch
    return document_ids


async def update_users_full_name(url, document_ids, user_full_name):
    response = await asks.post(
        url, json={**document_ids, **{"customerName": user_full_name}}
    )
    response.raise_for_status()


async def update_users_phone(url, document_ids, user_phone):
    response = await asks.post(
        url, json={**document_ids, **{"customerTelephone": user_phone}}
    )
    response.raise_for_status()


async def update_users_instagram(url, document_ids, user_instagram):
    response = await asks.post(
        url, json={**document_ids, **{"customerInstagram": user_instagram}}
    )
    response.raise_for_status()

    participant_number = response.json().get('number')
    if participant_number:
        return str(participant_number).zfill(4)
