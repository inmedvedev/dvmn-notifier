import requests
from requests.exceptions import ReadTimeout, ConnectionError
import telegram
from environs import Env
import time
import textwrap
import logging

logger = logging.getLogger('bot')


class TelegramLogsHandler(logging.Handler):

    def __init__(self, tg_bot, chat_id):
        super().__init__()
        self.chat_id = chat_id
        self.tg_bot = tg_bot

    def emit(self, record):
        log_entry = self.format(record)
        self.tg_bot.send_message(chat_id=self.chat_id, text=log_entry)


def request_for_events(headers, params, timeout=100):
    response = requests.get('https://dvmn.org/api/long_polling/', headers=headers, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def get_feedback_message(raw_response):
    attempt = raw_response['new_attempts'][0]
    lesson_title = attempt['lesson_title']
    lesson_url = attempt['lesson_url']
    is_negative = attempt['is_negative']
    if is_negative:
        return textwrap.dedent(
            f'''\
            У вас проверили работу «[{lesson_title}]({lesson_url})»\n
            К сожалению\, в работе нашлись ошибки\.'''
        )
    return textwrap.dedent(
        f'''\
        У вас проверили работу «[{lesson_title}]({lesson_url})»\n
        Преподавателю все понравилось\, можно приступать к следущему уроку\!'''
    )


if __name__ == '__main__':
    env = Env()
    env.read_env()
    chat_id = env.str('TG_CHAT_ID')
    tg_token = env.str('TELEGRAM_TOKEN')
    logger_tg_token = env.str('LOGGER_TELEGRAM_TOKEN')
    bot = telegram.Bot(token=tg_token)
    logger_bot = telegram.Bot(token=logger_tg_token)
    logger.setLevel(logging.INFO)
    logger.addHandler(TelegramLogsHandler(logger_bot, chat_id))
    logger.info('Бот запущен')
    headers = {'Authorization': env.str('DVMN_TOKEN')}
    params = {}
    while True:
        try:
            event = request_for_events(headers, params)
            if event['status'] == 'found':
                bot.send_message(text=get_feedback_message(event), chat_id=chat_id, parse_mode='MarkdownV2')
                params['timestamp'] = event['last_attempt_timestamp']
            elif event['status'] == 'timeout':
                params['timestamp'] = event['timestamp_to_request']
        except ConnectionError as error:
            time.sleep(5)
            continue
        except ReadTimeout:
            continue
        except Exception as error:
            logger.info('Бот упал с ошибкой:')
            logger.exception(error)

