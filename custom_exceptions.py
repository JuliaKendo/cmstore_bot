
SLUG_TO_EXCEPTION_TITLE = {
    'uncorrect_document_number': 'Вы ввели не корректный номер, введите 5 числовых символов',
    'document_not_found': 'Вы ввели не верный номер чека',
    'no_active_draw_found': 'Не найден активный розыгрыш',
    'does_not_match': 'Сумма чека не соответствует правилам розыгрыша',
    'uncorrect_user_full_name': 'Вы не верно ввели ФИО, введите в формате "Иванов Иван Иванович"',
    'uncorrect_user_phone': 'Вы не верно ввели номер телефона, введите в формате "79180000025"',
    'uncorrect_user_instagram': 'Вы не корректно ввели аккаунт инстаграмма, введите в формате "@...."',
    'invalid_instagram_account': 'Вы ввели недействительный аккаунт инстаграмма.',
    'unknown_error': 'Неизвестная ошибка'
}


class RequestError(Exception):

    def __init__(self, error_message):
        self.message = error_message
        super().__init__(self.message)

    def __str__(self):
        return self.message


class SmsApiError(Exception):

    def __init__(self, error_message):
        self.message = error_message
        super().__init__(self.message)

    def __str__(self):
        return self.message


class NotValidUserData(Exception):
    pass


class UncorrectDocumentNumber(NotValidUserData):

    def __str__(self):
        return SLUG_TO_EXCEPTION_TITLE.get('uncorrect_document_number', str(type(self)))


class DocumentNotFound(NotValidUserData):

    def __str__(self):
        return SLUG_TO_EXCEPTION_TITLE.get('document_not_found', str(type(self)))


class NoActiveDrawFound(NotValidUserData):

    def __str__(self):
        return SLUG_TO_EXCEPTION_TITLE.get('no_active_draw_found', str(type(self)))


class DocumentDoesNotMatch(NotValidUserData):

    def __str__(self):
        return SLUG_TO_EXCEPTION_TITLE.get('does_not_match', str(type(self)))


class UncorrectUserFullName(NotValidUserData):

    def __str__(self):
        return SLUG_TO_EXCEPTION_TITLE.get('uncorrect_user_full_name', str(type(self)))


class UncorrectUserPhone(NotValidUserData):

    def __str__(self):
        return SLUG_TO_EXCEPTION_TITLE.get('uncorrect_user_phone', str(type(self)))


class UncorrectUserInstagram(NotValidUserData):

    def __str__(self):
        return SLUG_TO_EXCEPTION_TITLE.get('uncorrect_user_instagram', str(type(self)))


class InvalidInstagramAccount(NotValidUserData):

    def __str__(self):
        return SLUG_TO_EXCEPTION_TITLE.get('invalid_instagram_account', str(type(self)))
