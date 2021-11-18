import logging

import rollbar
from aiogram.utils import exceptions

logger = logging.getLogger('cmstore-bot')


async def errors_handler(update, exception):
    """
    Exceptions handler. Catches all exceptions within task factory tasks.
    :param dispatcher:
    :param update:
    :param exception:
    :return: stdout logging
    """

    if isinstance(exception, exceptions.CantDemoteChatCreator):
        logging.error("Can't demote chat creator")
        rollbar.report_exc_info()
        return True

    if isinstance(exception, exceptions.TerminatedByOtherGetUpdates):
        logging.error('Terminated by other getUpdates request; Make sure that only one bot instance is running')
        rollbar.report_exc_info()
        return True

    if isinstance(exception, exceptions.MessageNotModified):
        logging.error('Message is not modified')
        rollbar.report_exc_info()
        return True

    if isinstance(exception, exceptions.MessageCantBeDeleted):
        logging.error('Message cant be deleted')
        rollbar.report_exc_info()
        return True

    if isinstance(exception, exceptions.MessageToDeleteNotFound):
        logging.error('Message to delete not found')
        rollbar.report_exc_info()
        return True

    if isinstance(exception, exceptions.MessageTextIsEmpty):
        logging.error('MessageTextIsEmpty')
        rollbar.report_exc_info()
        return True

    if isinstance(exception, exceptions.Unauthorized):
        logging.error(f'Unauthorized: {exception}')
        rollbar.report_exc_info()
        return True

    if isinstance(exception, exceptions.InvalidQueryID):
        logging.error(f'InvalidQueryID: {exception} \nUpdate: {update}')
        rollbar.report_exc_info()
        return True

    if isinstance(exception, exceptions.TelegramAPIError):
        logging.error(f'TelegramAPIError: {exception} \nUpdate: {update}')
        rollbar.report_exc_info()
        return True
    if isinstance(exception, exceptions.RetryAfter):
        logging.error(f'RetryAfter: {exception} \nUpdate: {update}')
        rollbar.report_exc_info()
        return True
    if isinstance(exception, exceptions.CantParseEntities):
        logging.error(f'CantParseEntities: {exception} \nUpdate: {update}')
        rollbar.report_exc_info()
        return True

    logging.error(f'Update: {update} \n{exception}')
    rollbar.report_exc_info()
