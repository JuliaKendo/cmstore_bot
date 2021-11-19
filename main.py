import re
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.utils.executor import start_polling
from aiogram.utils.exceptions import BadRequest
from contextlib import suppress
from environs import Env

from cmstore_lib import (
    read_file, read_config, is_valid_insta_account
)
from sms_api import send_sms
from notify_rollbar import notify_rollbar
from error_handler import errors_handler


env = Env()
env.read_env()

logger = logging.getLogger('cmstore-bot')


class ConversationSteps(StatesGroup):
    waiting_for_check_number = State()
    waiting_for_user_name = State()
    waiting_for_phone_number = State()
    waiting_for_insta = State()


async def set_commands(bot: Bot):
    commands = [
        types.BotCommand(command="/start", description="Запустить бота"),
        types.BotCommand(command="/cancel", description="Отменить текущее действие")
    ]
    await bot.set_my_commands(commands)


async def cmd_start(message: types.Message, state: FSMContext):
    await state.reset_state()
    with suppress(BadRequest):  # перехват ошибки здесь позволяет вывести текст без картинки.
        path_image = await read_config('startup_image')
        startup_photo = await read_file(path_image)
        await message.answer_photo(photo=startup_photo, reply_markup=types.ReplyKeyboardRemove())
    startup_text = await read_config('introduction_text')
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = ['Введите номер чека']
    keyboard.add(*buttons)
    await message.answer(
        eval('"' + startup_text.replace('"', '') + '"'),
        parse_mode=types.ParseMode.HTML,
        reply_markup=keyboard
    )


async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "Участие в розыгрыше отменено. Спасибо за проявленный интерес.",
        reply_markup=types.ReplyKeyboardRemove()
    )


async def cmd_check_number_input(message: types.Message):
    await ConversationSteps.waiting_for_check_number.set()


async def cmd_check_numbers_handle(message: types.Message, state: FSMContext):

    if not re.match(r'''^(\d{5})$''', message.text):
        await message.answer('Вы ввели не корректный номер, введите 5 числовых символов')
        return
    await state.update_data(check_number=message.text)

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = ['Завершить']
    keyboard.add(*buttons)
    await message.answer(
        'Введите свое Ф.И.О.:',
        parse_mode=types.ParseMode.MARKDOWN,
        reply_markup=keyboard
    )
    await ConversationSteps.next()


async def cmd_user_name_handle(message: types.Message, state: FSMContext):
    if not re.match(r'''([А-ЯЁ][а-яё]+[\-\s]?){3,}''', message.text):
        await message.answer('Вы не верно ввели ФИО, введите в формате "Иванов Иван Иванович"')
        return
    await state.update_data(user_name=message.text.lower())
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = ['Завершить']
    keyboard.add(*buttons)
    await message.answer(
        'Введите свой номер телефона:',
        parse_mode=types.ParseMode.MARKDOWN,
        reply_markup=keyboard
    )
    await ConversationSteps.next()


async def cmd_phone_number_handle(message: types.Message, state: FSMContext):
    if not re.match(r'''^(79\d{9})$''', message.text):
        await message.answer('Вы не верно ввели номер телефона, введите в формате "79180000025"')
        return
    await state.update_data(phone_number=message.text.lower())
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = ['Завершить']
    keyboard.add(*buttons)
    await message.answer(
        'Введите название своего аккаунта Instagram:',
        parse_mode=types.ParseMode.MARKDOWN,
        reply_markup=keyboard
    )
    await ConversationSteps.next()


async def cmd_instagram_handle(message: types.Message, state: FSMContext):
    if not re.match(r'''^@[a-zA-Z0-9-_.]{5,16}''', message.text):
        await message.answer('Вы не корректно ввели аккаунт инстаграмма, введите в формате "@...."')
        return
    valid_insta_account = await is_valid_insta_account(message.text)
    if not valid_insta_account:
        await message.answer('Вы ввели недействительный аккаунт инстаграмма."')
        return
    await state.update_data(instagram=message.text.lower())
    user_data = await state.get_data()
    logger.info(user_data)
    final_text = '''
Отлично, теперь Вы в игре😉
Ваш номер участника ХХХХ
Ждём 29 декабря в 15:00 на странице https://www.instagram.com/clinicmobile23/
'''
    await message.answer(
        final_text,
        parse_mode=types.ParseMode.MARKDOWN,
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.finish()
    # Вынести в декоратор, ибо может понадобиться информирование на других шагах
    dispatch_report = await send_sms(
        env.str('SMS_API_ID', ''), [user_data['phone_number']], final_text
    )
    # Добавить проверку статуса доставки и отправлять информацию в роллбар и логи
    logger.info(dispatch_report)


def register_handlers_common(dp: Dispatcher):
    # Регистрация общих обработчиков
    dp.register_message_handler(cmd_start, commands=['start'], state='*')
    dp.register_message_handler(cmd_cancel, commands=['cancel', 'exit', 'stop', 'quit'], state='*')
    dp.register_message_handler(cmd_cancel, Text(equals="завершить", ignore_case=True), state="*")
    # Шаг 1. Ввод и проверка номера чека
    dp.register_message_handler(cmd_check_number_input, text='Введите номер чека', state='*')
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


async def on_shutdown(dispatcher: Dispatcher):
    logger.info('Shutdown.')
    bot = dispatcher.bot
    # Close Redis connection.
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


async def on_startup(dispatcher: Dispatcher):
    logger.info('Startup.')
    bot = dispatcher.bot
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

    bot_token = env.str('TG_BOT_TOKEN')
    bot = Bot(token=bot_token)
    dp = Dispatcher(bot, storage=storage)

    # Обработчики логики бота
    register_handlers_common(dp)

    # Обработчики ошибок
    dp.register_errors_handler(errors_handler)

    start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown)


if __name__ == "__main__":
    main()
