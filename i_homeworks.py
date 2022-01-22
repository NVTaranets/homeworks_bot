import logging
import os
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

from exceptions import BotError
from bot_models import Base, Telegram

RETRY_TIME = 60
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

load_dotenv()

data_to_add = dict()
data_to_del = dict()


TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN_I')

updater = Updater(token=TELEGRAM_TOKEN)
# bot = telegram.Bot(token=TELEGRAM_TOKEN)

engine = create_engine('sqlite:///i_telegram.db')
s = sessionmaker()
s.configure(bind=engine)
session = s()
Base.metadata.create_all(engine)
bot = telegram.Bot(token=TELEGRAM_TOKEN)
cts = int(time.time())
last_message_error = ''
sends_messages = dict()
cts_dict = dict()

# Определяем константы этапов разговора
NAME, TOKEN, STARTED, SAVE = range(4)

NAME_1, SAVE_1 = range(4, 6)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'my_logger.log',
    maxBytes=50000000,
    backupCount=5
)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s'
)
handler.setFormatter(formatter)


def all_key_in_dict(keys, examine_dict):
    """проверяет наличее всех ключей в словаре."""
    return all([key in examine_dict for key in keys])


def send_message(bot, chat_id, message):
    """Отправка сообщения в чат телеграмма."""
    try:
        bot.send_message(chat_id, message)
        logger.info(f'Bot send message={message} to chat_id= {chat_id}')

    except Exception as error:
        logger.error('Ошибка при отправке сообщения в '
                     f'телеграмм {error} сообщение {message} '
                     f'to chat_id= {chat_id}')


def check_response(response):
    """Проверка правильности ответа API."""
    if not isinstance(response, dict):
        raise TypeError('От API домашки ожидался словарь в ответ на запрос!!!')
    if (all_key_in_dict(['homeworks', 'current_date'], response)):
        result = response['homeworks']
        if isinstance(result, list):
            return result
    raise BotError(f'Что то не так с ответом {response}')


def parse_status(homework):
    """Парсинг статуса домашней работы."""
    if not isinstance(homework, dict):
        raise TypeError('От API домашки ожидался словарь в '
                        'для расшифровки статуса работы!!!')
    if not (
        all_key_in_dict([
            'homework_name',
            'status',
            'date_updated'], homework)):
        raise KeyError('Нет необходимых ключей в словаре'
                       f' домашней работы {homework}')
    name = homework['homework_name']
    status = homework['status']
    if (isinstance(status, str)
            and (status in HOMEWORK_VERDICTS)):
        verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{name}". {verdict}'


def wake_up(update, context):
    """Функция обработки команды старт."""
    chat = update.effective_chat
    context.bot.send_message(chat_id=chat.id,
                             text='Спасибо, что включили меня')
    return ConversationHandler.END


def unknown(update, context):
    """Функция обработки неизвестных команд."""
    chat = update.effective_chat
    context.bot.send_message(chat_id=chat.id,
                             text='Простите, я вас не понял.')
    return ConversationHandler.END


def help(update, context):
    """Функция обработки команды /help."""
    chat = update.effective_chat
    context.bot.send_message(chat_id=chat.id,
                             text='''
Команды которые понимает бот:
/start - старт
/help - помощь
/about - о боте
/add_course - добавить курс
/del_course - удалить курс
/list_course - показать все курсы
/enable - разрешить проверку курса
/disable - запретить проверку курса
/dis_all - запретить все
/en_all - разрешить все
/clear - очистить настройки
''')
    return ConversationHandler.END


def about(update, context):
    """Функция обработки команды /about."""
    chat = update.effective_chat
    context.bot.send_message(chat_id=chat.id,
                             text='''
Бот написан для отслеживания изменения статусов проверки домашних работ \
студентов Яндекс практикума через запросы  к API сервиса Практикум.Домашка.
На данный момент проверена работа с API для курса "Python-developer-plus.
Для доступа к сервису необходимо сообщить боту свой токен узнать который \
можно по ссылке \
https://oauth.yandex.ru/authorize?response_type=token&client_id=1d0b9dd4d652455a9eb710d450ff456a
курс можно добавить по комаде /add_course
список добавленных курсов посмотреть по команде /list_course
''')
    return ConversationHandler.END


def add_course(update, context):
    """Функция обработки команды /add_course."""
    chat = update.effective_chat
    user = update.message.from_user
    data_to_add[update.effective_chat.id] = ''
    logger.info(
        f"Пользователь {user.first_name} начал процесс добавление курса"
    )
    context.bot.send_message(
        chat_id=chat.id,
        text='''
Как называется курс статус домашки которого вы \
хотели бы добавить в отслеживаемые?
Его название должно быть уникальным для вас.
(введите команду /cancel_add если хотите прервать диалог добавления курса)
'''
    )
    return NAME


def name_add(update, context):
    """обработка этапов 'беседы'."""
    user = update.message.from_user
    # проверяем дублирование наименований курсов
    imput_name=' '.join(update.message.text.split())
    course_count = (
        session.query(Telegram)
        .filter(Telegram.chat_id == update.effective_chat.id,
                Telegram.name == imput_name)
    ).count()
    if course_count == 0:
        logger.info(
            f'Новый курс {user.first_name}: c именем = {imput_name}'
        )
        data_to_add[update.effective_chat.id] = imput_name
        update.message.reply_text(
            'Хорошо, сообщи мне ТОКЕН доступа к ENDPOINT сервиса '
            'проверки статуса ДЗ, или отправь /cancel_add, если передумал.',
        )
        return TOKEN
    logger.info(
        f'Новый курс {user.first_name}: c именем = {imput_name}'
        ' уже существует нужно другое имя!!!'
    )
    update.message.reply_text(
        '''
Упс... А курс с таким именем уже есть в твоем профиле(.
Придумай другое имя для курса
или отправь /cancel_add, если передумал.''',
    )
    return NAME


def token(update, context):
    """обработка этапов 'беседы'."""
    user = update.message.from_user
    # проверяем дублирование токенов
    token_count = (
        session.query(Telegram)
        .filter(Telegram.practicum_token == update.message.text)
    ).count()
    if token_count == 0:
        try:
            get_api_answer(0, update.message.text)
        except (BotError, Exception) as error:
            logger.error(
                f'Токен {user.first_name}: {update.message.text} '
                f'{error}')
            update.message.reply_text(
                f'Упс... Ошибка {error} при проверке токена .\r\n'
                'Токен неправильный или недоступен сервис проверки ДЗ. '
                'Введи другой токен отправь /cancel_add, и попробуй позже.',
            )
            return TOKEN

        logger.info(f'Токен {user.first_name}: {update.message.text}')
        data_to_add[update.effective_chat.id] = (
            data_to_add[update.effective_chat.id]
            + '\r\n' + update.message.text)
        reply_keyboard = [['Да', 'Нет']]
        markup_key = ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True
        )
        update.message.reply_text(
            'Активировать проверку статусов?',
            reply_markup=markup_key,)
        return STARTED
    logger.info(f'Токен {user.first_name}: {update.message.text} '
                ' уже существует!!!')
    update.message.reply_text(
        '''
Упс... А этот токен уже кем-то был выбран(.
Сообщи мне уникальный токен или отправь /cancel_add, если передумал.''',
    )
    return NAME


def started(update, context):
    """обработка этапов 'беседы'."""
    reply_keyboard = [['Сохранить', 'Отменить']]
    markup_key = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    data_to_add[update.effective_chat.id] = (
        data_to_add[update.effective_chat.id]
        + '\r\n' + update.message.text)
    update.message.reply_text(
        'Выберите действие?',
        reply_markup=markup_key,)
    return SAVE


def save(update, context):
    """обработка этапов 'беседы'."""
    user = update.message.from_user
    data_to_add[update.effective_chat.id] = (
        data_to_add[update.effective_chat.id]
        + '\r\n' + update.message.text)
    logger.info(
        f'Пользователь {user.first_name} '
        f'сообщил в беседе: {data_to_add[update.effective_chat.id]}',
    )
    update.message.reply_text(
        f'Ты рассказал:\r\n {data_to_add[update.effective_chat.id]}'
        '\r\nСпасибо! Надеюсь, когда-нибудь снова сможем поговорить.',
        reply_markup=ReplyKeyboardRemove()
    )
    data = data_to_add[update.effective_chat.id].split('\r\n')
    if data[3] == 'Сохранить':
        new = Telegram(
            chat_id=update.effective_chat.id,
            name=data[0],
            practicum_token=data[1],
            started=(data[2] == 'Да')
        )
        session.add(new)
        # Commit to the database
        session.commit()

    # уберем данные о содержании беседы пользователя
    data_to_add.pop(update.effective_chat.id, None)
    return ConversationHandler.END


# Обрабатываем команду /cancel_add если пользователь отменил разговор
def cancel_add(update, context):
    """обработка этапов 'беседы'."""
    user = update.message.from_user
    # Пишем в журнал о том, что пользователь не разговорчивый
    logger.info("Пользователь %s отменил добавление курса.", user.first_name)
    data_to_add[update.effective_chat.id] = (
        data_to_add[update.effective_chat.id]
        + '\r\n' + update.message.text)
    update.message.reply_text(
        'Мое дело предложить - Ваше отказаться.'
        ' Передумаешь - пиши.',
        reply_markup=ReplyKeyboardRemove()
    )
    # Заканчиваем разговор.
    data_to_add.pop(update.effective_chat.id, None)
    return ConversationHandler.END


def del_course(update, context):
    """Функция начала обработки команды /del_course."""
    chat = update.effective_chat
    user = update.message.from_user
    logger.info(
        f"Пользователь {user.first_name} начал процесс удаления курса"
    )
    context.bot.send_message(
        chat_id=chat.id,
        text='''
Как называется курс который вы \
хотели бы удалить из отслеживаемых?
Его название должно быть уникальным для вас.
(введите команду /cancel_del если хотите прервать диалог удаления курса)
'''
    )
    return NAME_1


def name_del(update, context):
    """обработка этапов 'беседы'."""
    user = update.message.from_user
    # проверяем наличие курса
    course = (
        session.query(Telegram)
        .filter(Telegram.chat_id == update.effective_chat.id,
                Telegram.name == update.message.text)
    ).count()
    if course > 0:
        logger.info(
            f'Курс {user.first_name}: c именем = "{update.message.text}"'
            ' выбран для удаления!!!'
        )
        reply_keyboard = [['Удалить', 'Отменить']]
        markup_key = ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True)
        update.message.reply_text(
            f'Подтверди (отмени) удаление курса "{update.message.text}" '
            'или отправь /cancel_del, если еще не решил что делать.',
            reply_markup=markup_key
        )
        data_to_del[update.effective_chat.id] = update.message.text
        return SAVE_1

    logger.info(
        f'Курс {user.first_name}: c именем = {update.message.text} '
        'выбранный для удаления не существует!!!'
    )
    update.message.reply_text(
        f'Курс {user.first_name}: c именем = {update.message.text} '
        'выбранный для удаления не существует!!!\r\n'
        'Введите правильное существующие имя курса или '
        'команду /cancel_del если хотите прервать диалог удаления курса.'
    )
    return NAME_1


def delete(update, context):
    """Функция завершения обработки команды /del_course."""
    user = update.message.from_user
    if update.message.text == 'Удалить':
        session.query(Telegram).filter(
            Telegram.name == data_to_del[update.effective_chat.id],
            Telegram.chat_id == update.effective_chat.id
        ).delete(synchronize_session='fetch')
        session.commit()
        logger.info(
            f'Курс {user.first_name}: c именем = '
            f'{data_to_del[update.effective_chat.id]} удален для '
            f'чата id= {update.effective_chat.id}. '
        )
        return ConversationHandler.END
    update.message.reply_text(
        'Хорошо, удалять ничего не будем).'
        ' Передумаешь - пиши.',
        reply_markup=ReplyKeyboardRemove()
    )
    # Заканчиваем разговор.
    data_to_del.pop(update.effective_chat.id, None)
    return ConversationHandler.END


# Обрабатываем команду /cancel_del если пользователь отменил разговор
def cancel_del(update, context):
    """обработка этапов 'беседы'."""
    user = update.message.from_user
    # Пишем в журнал о том, что пользователь не разговорчивый
    logger.info("Пользователь %s отменил удаление курса.", user.first_name)
    update.message.reply_text(
        'Удалять ничего не будем).'
        ' Передумаешь - пиши.',
        reply_markup=ReplyKeyboardRemove()
    )
    # Заканчиваем разговор.
    data_to_del.pop(update.effective_chat.id, None)
    return ConversationHandler.END


def list_course(update, context):
    """Функция обработки команды /list_course."""
    chat = update.effective_chat
    list_user_course = session.query(Telegram.name, Telegram.started).filter(
        Telegram.chat_id == update.effective_chat.id
    ).order_by(Telegram.started, Telegram.name).all()
    print_user_course = '\r\n'.join(
        [f'\"{a}\" - {"ВКЛ." if b else "ВЫКЛ."}' for a, b in list_user_course]
    )
    context.bot.send_message(
        chat_id=chat.id,
        text=f'Список ваших курсов: \r\n\r\n{print_user_course}'
    )
    return ConversationHandler.END


def enable(update, context):
    """Функция обработки команды /enable."""
    ...


def disable(update, context):
    """Функция обработки команды /enable."""
    ...


def dis_all(update, context):
    """Функция обработки команды /enable."""
    ...


def en_all(update, context):
    """Функция обработки команды /enable."""
    ...


def clear(update, context):
    """Функция обработки команды /enable."""
    ...


def text_processing(update, context):
    """Функция обработки входящего сообщения."""
    chat = update.effective_chat
    context.bot.send_message(
        chat_id=chat.id,
        text='''
Простите, я не умею вести просто беседы.
Введите комаду /about или /help для получения подробностей о моих умениях
'''
    )
    return ConversationHandler.END


def get_api_answer(current_timestamp, practicum_token):
    """Получение ответа от ENDPOINT практикума."""
    headers = {'Authorization': f'OAuth {practicum_token}'}
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        responce = requests.get(ENDPOINT, headers=headers, params=params)
        if responce.status_code == HTTPStatus.OK:
            return responce.json()
        raise BotError(
            'Неожиданный статус ответа при запросе '
            f'к API домашки: {responce.status_code}'
        )

    except Exception as error:
        raise BotError(f'Ошибка при запросе к API домашки: {error}')


def my_callback(context):
    """Функция выполняется периодически."""
    cts = int(time.time())
    logger.info(f'cts = {cts}')
    courses = (
        session.query(
            Telegram.name,
            Telegram.chat_id,
            Telegram.practicum_token)
        .filter(Telegram.started)
    ).all()
    for t_name, t_chat_id, p_token in courses:
        n_cns = cts_dict.setdefault(t_chat_id, cts)
        try:
            response = get_api_answer(n_cns, p_token)
            logger.info(f'response={response} for chat_id={t_chat_id}')
            homeworks = check_response(response)
            for homework in homeworks:
                message = parse_status(homework)
                # наличие ключа проверено в функции parse_status
                mark_messages = (
                    f'{t_chat_id}{message}{homework["date_updated"]}'
                )

                if not (mark_messages
                        in sends_messages.setdefault(
                            t_chat_id,
                            list()
                        )
                        ):
                    send_message(bot, t_chat_id, message)
                    sends_messages[t_chat_id].append(mark_messages)
            cts_dict[t_chat_id] = response['current_date']

        except (BotError, Exception) as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)


def main():
    """Основная логика работы бота."""
    if not TELEGRAM_TOKEN:
        logger.critical(
            'Отсутствует обязательная переменная окружения:'
            '"TELEGRAM_TOKEN".'
        )
        exit()

    c_h_add_course = ConversationHandler(  # здесь строится логика разговора
        # точка входа в разговор
        entry_points=[CommandHandler('add_course', add_course)],
        # этапы разговора, каждый со своим списком обработчиков сообщений
        states={
            NAME: [MessageHandler(Filters.text & ~Filters.command, name_add)],
            TOKEN: [MessageHandler(Filters.text & ~Filters.command, token)],
            STARTED: [MessageHandler(Filters.regex('^(Да|Нет)$'), started)],
            SAVE: [MessageHandler(
                Filters.regex('^(Сохранить|Отменить)$'), save)],
        },
        # точка выхода из разговора
        fallbacks=[CommandHandler('cancel_add', cancel_add)],
    )
    c_h_del_course = ConversationHandler(  # здесь строится логика разговора
        # точка входа в разговор
        entry_points=[CommandHandler('del_course', del_course)],
        # этапы разговора, каждый со своим списком обработчиков сообщений
        states={
            NAME_1: [MessageHandler(
                Filters.text & ~Filters.command, name_del)
            ],
            SAVE_1: [MessageHandler(
                Filters.regex('^(Удалить|Отменить)$'), delete)
            ],
        },
        # точка выхода из разговора
        fallbacks=[CommandHandler('cancel_del', cancel_del)],
    )

    updater.dispatcher.add_handler(CommandHandler('start', wake_up))
    updater.dispatcher.add_handler(CommandHandler('about', about))
    updater.dispatcher.add_handler(CommandHandler('help', help))
    updater.dispatcher.add_handler(CommandHandler('list_course', list_course))
    updater.dispatcher.add_handler(CommandHandler('enable', enable))
    updater.dispatcher.add_handler(CommandHandler('disable', disable))
    updater.dispatcher.add_handler(CommandHandler('dis_all', dis_all))
    updater.dispatcher.add_handler(CommandHandler('en_all', en_all))
    updater.dispatcher.add_handler(CommandHandler('clear', clear))
    updater.dispatcher.add_handler(c_h_add_course)
    updater.dispatcher.add_handler(c_h_del_course)
    updater.dispatcher.add_handler(MessageHandler(Filters.command, unknown))
    updater.dispatcher.add_handler(
        MessageHandler(Filters.text, text_processing)
    )

    logger.info("Запущен бот")
    updater.job_queue.run_repeating(
        my_callback,
        interval=RETRY_TIME,
        first=0,
        name="my_job"
    )
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()