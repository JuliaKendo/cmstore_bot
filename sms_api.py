import asks
import functools

from contextlib import suppress
from custom_exceptions import SmsApiError


async def request_sms(method, api_id='', payload={}, login='', password=''):
    """Send request to SMS.ru service.

    Args:
        method (str): API method. E.g. 'send' or 'status'.
        api_id (str): Uniq id for account on SMS.ru. If empty, your need login and password
        login (str): Login for account on SMS.ru. Optional.
        password (str): Password for account on SMS.ru. Optional.
        payload (dict): Additional request params, override default ones.
    Returns:
        dict: Response from SMS.ru API.
    Raises:
        SmsApiError: If SMS.ru API response status is more then 103 or it has `"ERROR" in response.

    Examples:
        >>> request_sms("send", "my_api_id", {"phones": "+79123456789"})
        {"status_code": 1, "sms_id": 24}
        >>> request_sms("status", "my_api_id", {"phone": "+79123456789", "sms_id": "24"})
        {'status': "OK", 'status_code': 103, 'status_text': "Сообщение доставлено"}
    """

    url = f'https://sms.ru/sms/{method}'
    if api_id:
        params = {
            'api_id': api_id
        }
    else:
        params = {
            'login': login,
            'password': password,
        }
    print(payload)
    with suppress(asks.errors.BadStatus):
        responce = await asks.get(url, params={**params, **payload})
        responce.raise_for_status()
        reply = responce.json()
        if not reply.get('error'):
            return reply

    raise SmsApiError(responce.text)


async def send_sms(api_id, phones, text_message):

    dispatch_report = await request_sms(
        "send", api_id,
        {'to': ','.join(phones), 'msg': text_message, 'json': 1, 'test': 1}
    )
    return [{
        'phone': phone,
        'status_code': dispatch_report['sms'][phone]['status_code'],
        'sms_id': dispatch_report['sms'][phone]['sms_id']
    } for phone in phones]


async def check_sms_delivery(api_id, dispatch_reports):
    sms_delivery_reports = []
    for dispatch_report in dispatch_reports:
        sms_id = dispatch_report['sms_id']
        sms_delivery_report = await request_sms(
            "status", api_id, {'sms_id': sms_id, 'json': 1}
        )
        sms_delivery_reports.append({
            'phone': dispatch_report['phone'],
            'status': sms_delivery_report['sms'][sms_id]['status'],
            'status_code': sms_delivery_report['sms'][sms_id]['status_code'],
            'status_text': sms_delivery_report['sms'][sms_id]['status_text']
        })
    return sms_delivery_reports


def handle_sms():
    def decorator(func):
        @functools.wraps(func)
        async def inner(*args, **kwargs):
            with suppress(TypeError, ValueError, KeyError):
                user_data, final_text = await func(*args, **kwargs)
                api_id = args[0].bot.data['sms_api_id']
                dispatch_reports = await send_sms(
                    api_id, [user_data['phone_number']], final_text
                )
                sms_delivery_reports = await check_sms_delivery(api_id, dispatch_reports)
                unsuccessful_sms_delivery = [
                    sms_delivery_report for sms_delivery_report in sms_delivery_reports if (
                        sms_delivery_report['status_code'] >= 104 or sms_delivery_report['status_code'] == -1
                    )
                ]
                if unsuccessful_sms_delivery:
                    raise SmsApiError(unsuccessful_sms_delivery)
        return inner
    return decorator
