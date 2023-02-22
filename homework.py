"""Проверяет статус домашней работы."""
import json
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
    logger.critical('Отсутствуют обязательные переменные окружения')
    for key, value in TOKENS.items():
        if not value:
            logger.critical(
                f'Отсутствует обязательная переменная окружения {key}')
    raise Exception('Программа принудительно остановлена.')


def send_message(bot, message):
    """Отправляет сообщение в чат телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Сообщение отправлено {message}')
    except Exception:
        logger.error(f'Не удалось отправить сообщение {message}')


def check_json(response):
    """Проверяет формат Json."""
    try:
        if __name__ == '__main__':
            json.loads(response)
        send_once('json_error')
    except json.JSONDecodeError as error:
        if send_once('json_error', str(error), True):
            this_bot.get('bot')('Неверный формат Json')
        logger.error('Неверный формат Json')


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
            this_bot.get('bot')(f'Код ответа API {status_code}')
            raise Exception
        else:
            send_once('request_error')

            json_data = response.json()
            check_json(response.text)
            if isinstance(json_data, dict):
                if isinstance(json_data['homeworks'], list):
                    return json_data
    except requests.RequestException as request_error:
        if send_once('request_error', request_error, True):
            this_bot.get('bot')('Ошибка ответа сервера API практикум')
        logger.error('Ошибка ответа сервера API практикум')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        this_bot.get('bot')('Неверный формат ответа')
        logger.error('Неверный формат ответа API практикум')
        raise TypeError
    if 'homeworks' not in response:
        this_bot.get('bot')('Отсутствует ключ homeworks')
        logger.error('Отсутствует ключ homeworks')
        raise Exception
    if not isinstance(response.get('homeworks'), list):
        this_bot.get('bot')('Неверный формат ответа')
        logger.error('Неверный формат ответа API практикумю')
        raise TypeError
    return True


def parse_status(homework):
    """Возвращает статус проверки домашней работы."""
    verdict = homework.get('status')
    if verdict not in HOMEWORK_VERDICTS.keys():
        this_bot.get('bot')(f'Неожиданный статус домашней работы {verdict}')
        logger.error(f'Неожиданный статус домашней работы {verdict}')
        raise UnexpectedStatus
    if 'homework_name' not in homework:
        this_bot.get('bot')('Отсутсвует ключ homework_name')
        logger.error('Отсутсвует ключ homework_name')
        raise Exception
    homework_name = homework.get('homework_name')
    if os.environ.get('verdict') != verdict:
        os.environ['verdict'] = verdict
        homework_name = homework.get('homework_name')
        return (f'Изменился статус проверки работы "{homework_name}".'
                f'{verdict}\n{HOMEWORK_VERDICTS.get(verdict)}')
    logger.debug('Статус не изменился')
    return


def check_bot(bot):
    """Проверяет что бот запустился."""
    if str(bot) == BOT:
        return True
    else:
        raise Exception


def check_timestamp(timestamp):
    """Проверяет формат даты для запроса данных API."""
    if isinstance(timestamp, int) and datetime.fromtimestamp(timestamp):
        send_once('date_error')
        return
    if send_once('date_error', 'Неверный формат даты', True):
        this_bot.get('bot')('Неверный формат даты')
        logger.error('Неверный формат даты')
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
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.error(message)
            raise error
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
