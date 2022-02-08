import requests
from requests.exceptions import ReadTimeout, ConnectionError
import telegram
from environs import Env
import time
import textwrap


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
    telegram_token = env.str('TELEGRAM_TOKEN')
    bot = telegram.Bot(token=telegram_token)
    chat_id = env.str('TG_CHAT_ID')
    headers = {'Authorization': env.str('DVMN_TOKEN')}
    params = {}
    while True:
        try:
            event = request_for_events(headers, params)
        except ConnectionError as error:
            time.sleep(5)
            continue
        except ReadTimeout:
            continue
        if event['status'] == 'found':
            bot.send_message(text=get_feedback_message(event), chat_id=chat_id, parse_mode='MarkdownV2')
            params['timestamp'] = event['last_attempt_timestamp']
        elif event['status'] == 'timeout':
            params['timestamp'] = event['timestamp_to_request']
