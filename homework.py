"""Проверяет статус домашней работы."""
import logging
import os
import sys
import time
from datetime import datetime
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import UnexpectedStatus

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
BOT = os.getenv('BOT')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

TOKENS = {
    'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
    'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
    'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
}

REQUIRED_VALUES_NOT_FOUND = 'Отсутствуют обязательные переменные окружения'
REQUIRED_VALUE_NOT_FOUND = ('Отсутствует обязательная'
                            'переменная окружения {}')
PROGRAM_STOPPED = 'Программа принудительно остановлена.'
MESSAGE_SEND = 'Сообщение отправлено {}'
MESSAGE_NOT_SEND = 'Не удалось отправить сообщение {}'
API_ANSWER_CODE = 'Код ответа API {}'
WRONG_JSON = 'Неверный формат Json'
WRONG_ANSWER_PRACTICUM_API = 'Ошибка ответа сервера API практикум'
WRONG_FORMAT_PRACTICUM_API = 'Неверный формат ответа API практикум'
HOMEWORKS_KEY_NOT_EXISTS = 'Отсутствует ключ homeworks'
UNEXPECTED_HOMEWORK_STATUS = 'Неожиданный статус домашней работы {}'
HOMEWORKS_NAME_KEY_NOT_EXISTS = 'Отсутсвует ключ homework_name'
STATUS_CHANGE = 'Изменился статус проверки работы \"{}\".\n{}'
STATUS_NOT_CHANGE = 'Статус не изменился'
UNEXPECTED_DATE_FORMAT = 'Неверный формат даты'
PROGRAM_ERROR = 'Сбой в работе программы: {error}'

this_bot = {}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(message)s,',
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)


def send_once(key, value='No errors', set=False):
    """Проверяет что сообщение об ошибке уже отправлено."""
    if set:
        if (os.environ.get(f'{key}') != value):
            os.environ[f'{key}'] = value
            return True
        else:
            return False
    else:
        os.environ[f'{key}'] = value
        return True


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = (TELEGRAM_CHAT_ID, PRACTICUM_TOKEN, TELEGRAM_TOKEN)
    if all(tokens):
        return True
    logger.critical(REQUIRED_VALUES_NOT_FOUND)
    for key, value in TOKENS.items():
        if not value:
            logger.critical(REQUIRED_VALUE_NOT_FOUND.format(key))
    raise Exception(PROGRAM_STOPPED)


def send_message(bot, message):
    """Отправляет сообщение в чат телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(MESSAGE_SEND.format(message))
    except Exception:
        logger.error(MESSAGE_NOT_SEND.format(message))


def get_api_answer(timestamp):
    """Запрашивает API практикум."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        status_code = response.status_code
        if status_code != HTTPStatus.OK:
            this_bot.get('bot')(API_ANSWER_CODE.format(status_code))
            raise Exception
        else:
            send_once('request_error')
            try:
                json_data = response.json()
                send_once('json_error')
            except Exception as error:
                if send_once('json_error', str(error), True):
                    this_bot.get('bot')(WRONG_JSON)
                logger.error(WRONG_JSON)
            return json_data
    except requests.RequestException as request_error:
        if send_once('request_error', request_error, True):
            this_bot.get('bot')(WRONG_ANSWER_PRACTICUM_API)
        logger.error(WRONG_ANSWER_PRACTICUM_API)


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        this_bot.get('bot')(WRONG_FORMAT_PRACTICUM_API)
        logger.error(WRONG_FORMAT_PRACTICUM_API)
        raise TypeError
    if 'homeworks' not in response:
        this_bot.get('bot')(HOMEWORKS_KEY_NOT_EXISTS)
        logger.error(HOMEWORKS_KEY_NOT_EXISTS)
        raise Exception
    if not isinstance(response.get('homeworks'), list):
        this_bot.get('bot')(WRONG_FORMAT_PRACTICUM_API)
        logger.error(WRONG_FORMAT_PRACTICUM_API)
        raise TypeError
    return True


def parse_status(homework):
    """Возвращает статус проверки домашней работы."""
    verdict = homework.get('status')
    if verdict not in HOMEWORK_VERDICTS.keys():
        this_bot.get('bot')(UNEXPECTED_HOMEWORK_STATUS.format(verdict))
        logger.error(UNEXPECTED_HOMEWORK_STATUS.format(verdict))
        raise UnexpectedStatus
    if 'homework_name' not in homework:
        this_bot.get('bot')(HOMEWORKS_NAME_KEY_NOT_EXISTS)
        logger.error(HOMEWORKS_NAME_KEY_NOT_EXISTS)
        raise Exception
    homework_name = homework.get('homework_name')
    if os.environ.get('verdict') != verdict:
        os.environ['verdict'] = verdict
        homework_name = homework.get('homework_name')
        return (
            STATUS_CHANGE.format(
                homework_name, HOMEWORK_VERDICTS.get(verdict)))
    logger.debug(STATUS_NOT_CHANGE)
    return


def check_bot(bot):
    """Проверяет что бот запустился."""
    if bot.get_me().is_bot:
        return True
    else:
        raise Exception


def check_timestamp(timestamp):
    """Проверяет формат даты для запроса данных API."""
    if isinstance(timestamp, int) and datetime.fromtimestamp(timestamp):
        send_once('date_error')
        return
    if send_once('date_error', UNEXPECTED_DATE_FORMAT, True):
        this_bot.get('bot')(UNEXPECTED_DATE_FORMAT)
        logger.error(UNEXPECTED_DATE_FORMAT)
    return True


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    if __name__ == '__main__':
        check_bot(bot)

    def my_bot(message):
        bot.send_message(TELEGRAM_CHAT_ID, message)
    this_bot['bot'] = my_bot
    timestamp = int(time.time() - 7000000)
    homeworks = ''
    while True:
        try:
            api_answer = get_api_answer(timestamp - 7000000)
            check_response(api_answer)
            timestamp = api_answer.get('current_date')
            if check_timestamp(timestamp):
                continue
            homeworks = api_answer.get('homeworks')
            if len(homeworks) > 0:
                status_message = parse_status(homeworks[0])
                if status_message:
                    send_message(bot, status_message)
        except Exception as error:
            message = PROGRAM_ERROR.format(error)
            send_message(bot, message)
            logger.error(message)
            raise error
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
