import re
import config
import rollbar
import asyncio
import logging
import functools
import multiprocessing

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text, Filter
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.utils.executor import start_polling, start_webhook
from aiogram.utils.exceptions import (
    BadRequest, MessageCantBeDeleted, MessageToDeleteNotFound
)
from contextlib import suppress
from collections import defaultdict
from environs import Env
from requests import HTTPError, ConnectionError
from pathlib import Path

from cmstore_lib import (
    read_file,
    read_config,
    init_insta_bot,
    get_document_identifiers_from_service,
    update_users_full_name,
    update_users_phone,
    update_users_instagram
)
from custom_exceptions import (
    DocumentNotFound,
    NoActiveDrawFound,
    DocumentDoesNotMatch,
    IncorrectDocumentNumber,
    IncorrectUserFullName,
    IncorrectUserPhone,
    IncorrectUserInstagram,
    InvalidInstagramAccount,
    SmsApiError,
    DocumentParticipatedInDraw
)
from sms_api import handle_sms
from notify_rollbar import notify_rollbar
from error_handler import errors_handler
from monitoring_lib import handle_monitoring_log

env = Env()
env.read_env()

logger = logging.getLogger('cmstore-bot')
messages_for_remove = defaultdict(list)


class ConversationSteps(StatesGroup):
    waiting_for_check_number = State()
    waiting_for_user_name = State()
    waiting_for_phone_number = State()
    waiting_for_insta = State()


class IncorrectUserInput(Filter):

    def __init__(self, text) -> None:
        self.text = text
        super().__init__()

    async def check(self, message: types.Message):
        state = Dispatcher.get_current().current_state()
        current_state = await state.get_state()
        return not (message.text == self.text or current_state)


def handle_mistakes():
    def decorator(func):
        @functools.wraps(func)
        async def inner(*args, **kwargs):
            try:
                await func(*args, **kwargs)
            except (
                DocumentNotFound,
                NoActiveDrawFound,
                DocumentDoesNotMatch,
                IncorrectDocumentNumber,
                IncorrectUserFullName,
                IncorrectUserPhone,
                IncorrectUserInstagram,
                InvalidInstagramAccount,
                DocumentParticipatedInDraw
            ) as description:
                await args[0].answer(description)
            except SmsApiError as error:
                logger.error(f'Ошибки отправки sms: {error}')
                rollbar.report_exc_info()
            except (HTTPError, ConnectionError) as error:
                logger.error(f'Ошибка отправки http запроса в 1С: {error}')
                rollbar.report_exc_info()
        return inner
    return decorator


def handle_delete_messages(delete=False):
    def decorator(func):
        @functools.wraps(func)
        async def inner(*args, **kwargs):
            message_seq = await func(*args, **kwargs)
            chat_id = args[0].bot.data['chat_ids_deleted_messages']
            if isinstance(message_seq, list):
                for message in message_seq:
                    if message['chat']['id'] != chat_id:
                        continue
                    messages_for_remove[message['chat']['id']].append(message)
            else:
                if message_seq['chat']['id'] == chat_id:
                    messages_for_remove[message_seq['chat']['id']].append(message_seq)
            if delete:
                # Удаляем все сообщения при финишировании стейт машины.
                asyncio.create_task(delete_messages(message_seq[0]['chat']['id']))
        return inner
    return decorator


async def delete_messages(chat_id):
    for message in messages_for_remove[chat_id]:
        await asyncio.sleep(5)
        with suppress(MessageCantBeDeleted, MessageToDeleteNotFound):
            await message.delete()
    messages_for_remove[chat_id] = []


@handle_delete_messages()
@handle_monitoring_log()
async def show_answer(message, text, image=None):
    result = [message]
    with suppress(BadRequest):  # перехват ошибки здесь позволяет вывести текст без картинки.
        media_msg = await message.answer_photo(photo=image)
        result.append(media_msg)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = ['Отказаться от участия']
    keyboard.add(*buttons)
    msg = await message.answer(
        text,
        parse_mode=types.ParseMode.MARKDOWN,
        reply_markup=keyboard
    )
    result.append(msg)
    return result[::-1]


@handle_delete_messages(True)
@handle_monitoring_log()
async def handle_finish(message, state, closing_text):
    await state.finish()
    msg = await message.answer(
        closing_text,
        parse_mode=types.ParseMode.MARKDOWN,
        reply_markup=types.ReplyKeyboardRemove()
    )
    return [msg, message]


async def set_commands(bot: Bot):
    commands = [
        types.BotCommand(command="/start", description="Запустить бота"),
        types.BotCommand(command="/cancel", description="Отменить текущее действие")
    ]
    await bot.set_my_commands(commands)


@handle_delete_messages()
@handle_monitoring_log()
async def cmd_start(message: types.Message, state: FSMContext):
    result = [message]
    await state.reset_state()
    with suppress(BadRequest):  # перехват ошибки здесь позволяет вывести текст без картинки.
        path_image = await read_config('startup_image')
        startup_photo = await read_file(path_image)
        media_msg = await message.answer_photo(photo=startup_photo, reply_markup=types.ReplyKeyboardRemove())
        result.append(media_msg)
    startup_text = await read_config('introduction_text')
    prepared_text = eval('"' + startup_text.replace('"', '') + '"')
    # Иногда в зависимости от операционной системы встречается двойное экранирование
    # управляющих последовательностей "\\\\r\\\\n\\\\t", данный код гарантирует удаление
    # всех экранируемых символов
    for _ in range(0, 3):
        with suppress(SyntaxError):
            prepared_text = eval('"' + prepared_text.replace('"', '') + '"')
            continue
        break
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = ['Ввести номер чека']
    keyboard.add(*buttons)
    msg = await message.answer(
        prepared_text,
        parse_mode=types.ParseMode.MARKDOWN,
        reply_markup=keyboard
    )
    result.append(msg)
    return result[::-1]


async def cmd_cancel(message: types.Message, state: FSMContext):
    await handle_finish(
        message, state,
        "Участие в розыгрыше отменено. Спасибо за проявленный интерес."
    )


@handle_delete_messages()
@handle_monitoring_log()
async def cmd_confirm_finish(message: types.Message, state: FSMContext):
    keyboard = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton(text="Да", callback_data="finish"),
        types.InlineKeyboardButton(text="Нет", callback_data="continue")
    ]
    keyboard.add(*buttons)
    msg = await message.answer(
        "Вы действительно хотите отказаться от участия в розыгрыше?", reply_markup=keyboard
    )
    return [msg, message]


@handle_delete_messages()
@handle_monitoring_log()
async def cmd_incorrect_user_input(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = ['Ввести номер чека']
    keyboard.add(*buttons)
    msg = await message.answer(
        'Для участия в розыгрыше нажмите кнопку "Ввести номер чека"',
        reply_markup=keyboard
    )
    return [msg, message]


@handle_delete_messages()
@handle_monitoring_log()
async def cmd_check_number_input(message: types.Message):
    await ConversationSteps.waiting_for_check_number.set()
    return message


@handle_mistakes()
async def cmd_check_numbers_handle(message: types.Message, state: FSMContext):
    if not re.match(r'''^(\d{5})$''', message.text):
        raise IncorrectDocumentNumber
    document_ids = await get_document_identifiers_from_service(
        message.bot.data['1c_url'], message.text
    )
    await state.update_data(document=document_ids)
    await show_answer(message, 'Введите свое Ф.И.О. (в формате "Иванов Иван Иванович"):')
    await ConversationSteps.next()


@handle_mistakes()
async def cmd_user_name_handle(message: types.Message, state: FSMContext):
    if not re.match(r'''([А-ЯЁ][а-яё]+[\-\s]?){3,}''', message.text):
        raise IncorrectUserFullName
    user_full_name = message.text.lower()
    user_data = await state.get_data()
    await update_users_full_name(
        message.bot.data['1c_url'], user_data['document'], user_full_name
    )
    await state.update_data(user_name=user_full_name)
    await show_answer(message, 'Введите свой номер телефона (в формате "79180000025"):')
    await ConversationSteps.next()


@handle_mistakes()
async def cmd_phone_number_handle(message: types.Message, state: FSMContext):
    if not re.match(r'''^([78]?9\d{9})$''', message.text):
        raise IncorrectUserPhone
    user_data = await state.get_data()
    await update_users_phone(
        message.bot.data['1c_url'], user_data['document'], message.text
    )
    await state.update_data(phone_number=message.text)
    img = await read_file(Path(config.MEDIAFILES_DIRS, 'demo_insta.jpg'))
    await show_answer(message, 'Введите название своего аккаунта Instagram:', img)
    await ConversationSteps.next()


@handle_mistakes()
@handle_sms()
async def cmd_instagram_handle(message: types.Message, state: FSMContext):
    if not re.match(r'''^@?[a-zA-Z0-9-_.]{5,16}''', message.text):
        raise IncorrectUserInstagram
    user_data = await state.get_data()
    participant_number = await update_users_instagram(
        message.bot.data['1c_url'], user_data['document'], message.text
    )
    await state.update_data(instagram=message.text)
    final_text = f'''
Отлично, теперь Вы в игре😉
Ваш номер участника {participant_number if participant_number else ""}
Ждём 29 декабря в 15:00 на странице [@clinicmobile23](https://www.instagram.com/clinicmobile23/).

*Данное сообщение продублировано Вам в СМС.*
'''
    await handle_finish(message, state, final_text)
    return user_data, final_text


async def send_finish(call: types.CallbackQuery):
    state = Dispatcher.get_current().current_state()
    await handle_finish(
        call.message, state,
        'Участие в розыгрыше отменено. Благодарим за проявленный интерес.'
    )
    await call.answer(text="Спасибо, что воспользовались ботом!", show_alert=True)


async def send_continue(call: types.CallbackQuery):
    state = Dispatcher.get_current().current_state()
    current_state = await state.get_state()
    if current_state == 'ConversationSteps:waiting_for_user_name':
        await show_answer(call.message, 'Введите свое Ф.И.О. (в формате "Иванов Иван Иванович"):')
    elif current_state == 'ConversationSteps:waiting_for_phone_number':
        await show_answer(call.message, 'Введите свой номер телефона (в формате "79180000025"):')
    elif current_state == 'ConversationSteps:waiting_for_insta':
        img = await read_file(Path(config.MEDIAFILES_DIRS, 'demo_insta.jpg'))
        await show_answer(call.message, 'Введите название своего аккаунта Instagram:', img)
    else:
        await call.message.answer('Продолжить')
    await call.answer()


def register_handlers_common(dp: Dispatcher):
    # Регистрация общих обработчиков
    dp.register_message_handler(cmd_start, commands=['start'], state='*')
    dp.register_message_handler(cmd_cancel, commands=['cancel', 'exit', 'stop', 'quit'], state='*')
    dp.register_message_handler(cmd_confirm_finish, Text(equals="Отказаться от участия", ignore_case=True), state="*")
    dp.register_message_handler(cmd_incorrect_user_input, IncorrectUserInput('Ввести номер чека'))

    # Шаг 1. Ввод и проверка номера чека
    dp.register_message_handler(cmd_check_number_input, text='Ввести номер чека', state='*')
    dp.register_message_handler(
        cmd_check_numbers_handle, state=ConversationSteps.waiting_for_check_number
    )
    # Шаг 2. Обработка ввода ФИО пользователя
    dp.register_message_handler(
        cmd_user_name_handle, state=ConversationSteps.waiting_for_user_name
    )
    # Шаг 3. Обработка ввода номера телефона пользователя
    dp.register_message_handler(
        cmd_phone_number_handle, state=ConversationSteps.waiting_for_phone_number
    )
    # Шаг 4. Обработка ввода аккаунта инстаграм
    dp.register_message_handler(cmd_instagram_handle, state=ConversationSteps.waiting_for_insta)

    # Регистрация обработчиков коллбэков
    dp.register_callback_query_handler(send_finish, text="finish", state='*')
    dp.register_callback_query_handler(send_continue, text="continue", state='*')


async def on_shutdown(dispatcher: Dispatcher):
    logger.info('Shutdown.')
    bot = dispatcher.bot
    if bot.data['use_webhook']:
        await bot.delete_webhook()
    if bot.data['insta_bot']:
        bot.data['insta_bot'].logout()
    # Close Redis connection.
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


async def on_startup(dispatcher: Dispatcher):
    logger.info('Startup.')
    bot = dispatcher.bot
    if bot.data['use_webhook']:
        await bot.set_webhook(bot.data['webhook_url'])
    # Установка команд бота
    await set_commands(bot)


@notify_rollbar()
def main():

    logging.basicConfig(
        level='INFO',
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    )

    logger.info('Starting bot')

    storage = RedisStorage2(
        host=env.str('REDIS_HOST', 'localhost'),
        port=env.str('REDIS_PORT', '6379'),
        db='5'
    )

    bot = Bot(token=env.str('TG_BOT_TOKEN'))

    config.set_bot_variables(bot, env)

    if env.str('INSTA_LOGIN'):
        with suppress(SystemExit, multiprocessing.context.TimeoutError):
            bot.data['insta_bot'] = init_insta_bot(
                env.str('INSTA_LOGIN'), env.str('INSTA_PASSWORD')
            )

    dp = Dispatcher(bot, storage=storage)

    # Обработчики логики бота
    register_handlers_common(dp)

    # Обработчики ошибок
    dp.register_errors_handler(errors_handler)

    if bot.data['use_webhook']:
        start_webhook(
            dispatcher=dp,
            webhook_path='/webhook',
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            skip_updates=True,
            host=bot.data['webapp_host'],
            port=bot.data['webapp_port'],
        )
    else:
        start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown)


if __name__ == "__main__":
    main()
