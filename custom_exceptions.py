
SLUG_TO_EXCEPTION_TITLE = {
    'incorrect_document_number': 'Вы ввели не корректный номер, введите 4 числовых символов',
    'document_not_found': 'Вы ввели не верный номер чека',
    'document_number_participated_in_draw': 'Данный чек уже участвует в розыгрыше',
    'no_active_draw_found': 'Не найден активный розыгрыш',
    'does_not_match': 'Сумма чека не соответствует правилам розыгрыша',
    'incorrect_user_full_name': 'Вы не верно ввели ФИО, введите в формате "Иванов Иван Иванович"',
    'incorrect_user_phone': 'Вы не верно ввели номер телефона, введите в формате "79180000025"',
    'incorrect_user_instagram': 'Вы не корректно ввели аккаунт инстаграмма, введите в формате "@...."',
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


class IncorrectDocumentNumber(NotValidUserData):

    def __str__(self):
        return SLUG_TO_EXCEPTION_TITLE.get('incorrect_document_number', str(type(self)))


class DocumentNotFound(NotValidUserData):

    def __str__(self):
        return SLUG_TO_EXCEPTION_TITLE.get('document_not_found', str(type(self)))


class DocumentParticipatedInDraw(NotValidUserData):

    def __str__(self):
        return SLUG_TO_EXCEPTION_TITLE.get('document_number_participated_in_draw', str(type(self)))


class NoActiveDrawFound(NotValidUserData):

    def __str__(self):
        return SLUG_TO_EXCEPTION_TITLE.get('no_active_draw_found', str(type(self)))


class DocumentDoesNotMatch(NotValidUserData):

    def __str__(self):
        return SLUG_TO_EXCEPTION_TITLE.get('does_not_match', str(type(self)))


class IncorrectUserFullName(NotValidUserData):

    def __str__(self):
        return SLUG_TO_EXCEPTION_TITLE.get('incorrect_user_full_name', str(type(self)))


class IncorrectUserPhone(NotValidUserData):

    def __str__(self):
        return SLUG_TO_EXCEPTION_TITLE.get('incorrect_user_phone', str(type(self)))


class IncorrectUserInstagram(NotValidUserData):

    def __str__(self):
        return SLUG_TO_EXCEPTION_TITLE.get('incorrect_user_instagram', str(type(self)))


class InvalidInstagramAccount(NotValidUserData):

    def __str__(self):
        return SLUG_TO_EXCEPTION_TITLE.get('invalid_instagram_account', str(type(self)))
