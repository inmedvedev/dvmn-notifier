import requests
from requests.exceptions import ReadTimeout, ConnectionError
import telegram
from environs import Env


def request_for_events(headers, params, timeout=100):
    response = requests.get('https://dvmn.org/api/long_polling/', headers=headers, params=params, timeout=timeout)
    print(response.url)
    raw_response = response.json()
    print(raw_response)
    if raw_response['status'] == 'timeout':
        params['timestamp'] = raw_response['timestamp_to_request']
    elif raw_response['status'] == 'found':
        params['timestamp'] = raw_response['last_attempt_timestamp']
        return raw_response


def send_notification(token, chat_id, message):
    bot = telegram.Bot(token=token)
    bot.send_message(text=message, chat_id=chat_id, parse_mode='MarkdownV2')


def get_feedback_message(raw_response):
    attempt = raw_response['new_attempts'][0]
    lesson_title = attempt['lesson_title']
    lesson_url = attempt['lesson_url']
    is_negative = attempt['is_negative']
    if is_negative:
        return f'У вас проверили работу «[{lesson_title}]({lesson_url})»\n\n' \
               f'К сожалению\, в работе нашлись ошибки\.'
    return f'У вас проверили работу «[{lesson_title}]({lesson_url})»\n\n' \
           f'Преподавателю все понравилось\, можно приступать к следущему уроку\!'


if __name__ == '__main__':
    env = Env()
    env.read_env()
    telegram_token = env.str('TG_TOKEN')
    chat_id = env.str('CHAT_ID')
    headers = {'Authorization': env.str('DVMN_TOKEN')}
    params = {}
    while True:
        try:
            event = request_for_events(headers, params)
        except (ReadTimeout, ConnectionError) as error:
            print(error)
            continue
        if event:
            send_notification(telegram_token, chat_id, get_feedback_message(event))
