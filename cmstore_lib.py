import asks
import re
import yaml
import aiofiles
import requests

from contextlib import suppress
from urllib.parse import unquote_plus

from custom_exceptions import (
    RequestError,
    DocumentNotFound,
    NoActiveDrawFound,
    DocumentDoesNotMatch
)

service_url = 'https://cloud.sova.company/dev/cm/hs/sova_rozygrysh'


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
    with suppress(ValueError, requests.exceptions.ReadTimeout, AssertionError):
        _, nickname = re.split(r'^@', insta_name)
        response = requests.get(
            f'https://www.instagram.com/{nickname}/', verify=False, timeout=10
        )
        assert re.findall(r'''(%s)''' % insta_name, response.text)
        return True


async def get_document_identifiers_from_service(document_number):
    response = await asks.post(
        service_url, json={"documentNumber": document_number}
    )
    response.raise_for_status()

    document_ids = response.json()
    if document_ids['document'] == 'not found':
        raise DocumentNotFound
    if document_ids['document'] == 'no active draw found':
        raise NoActiveDrawFound
    if document_ids['document'] == 'does not match':
        raise DocumentDoesNotMatch
    return document_ids


async def update_users_full_name(document_ids, user_full_name):
    response = await asks.post(
        service_url, json={**document_ids, **{"customerName": user_full_name}}
    )
    response.raise_for_status()


async def update_users_phone(document_ids, user_phone):
    response = await asks.post(
        service_url, json={**document_ids, **{"customerTelephone": user_phone}}
    )
    response.raise_for_status()


async def update_users_instagram(document_ids, user_instagram):
    response = await asks.post(
        service_url, json={**document_ids, **{"customerInstagram": user_instagram}}
    )
    response.raise_for_status()
