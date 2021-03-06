#!/usr/bin/env python
# -*- coding: utf8 -*-
import random
import time

import emoji
import vk_api

from cfg.config import BOT_SIGN_IN, LITERALS, ADMIN_LIST, VERSION, DBSETTINGS
from database.dbconnector import DBConnector
from database.logger import Logger
from lib.botmath import BotMath
from lib.newsparser import NewsParser


class BotEngine(object):
    def __init__(self):
        self.__disable = False
        self.__is_intelligent = False

        self._vk_session = vk_api.VkApi(
            BOT_SIGN_IN['login'],
            BOT_SIGN_IN['password'],
            captcha_handler=self.__captcha_handler
        )

        try:
            self._vk_session.authorization()
        except vk_api.AuthorizationError as error_msg:
            print(error_msg)
            return

        self._logger = Logger()
        try:
            self._db = DBConnector(
                DBSETTINGS['user'],
                DBSETTINGS['password'],
                DBSETTINGS['host'],
                DBSETTINGS['port'],
                DBSETTINGS['database']
            )
        except Exception as error_msg:
            print('[DATABASE] Error: %s' % error_msg)
            self._db = None

        self._news = NewsParser()
        self._math = BotMath()

        self._vk = self._vk_session.get_api()

        self._ignore_msgs = self._logger.read_history()

        self._bot_name = self._get_user_name(None)

        self.__ans_list = []
        self.__msg_list = []
        self.__intell__ans_list = []
        self.__intell__msg_list = []
        self.__update_messages()

    def __update_messages(self):
        u"""
            Метод используемый для обновления списков с айдишниками сообщений.
            Используется после добавления/удаления нового сообщения.
        """
        if self._db:
            self.__ans_list = self._db.select_ids(is_question_answer=True)
            self.__msg_list = self._db.select_ids()

            self.__intell__ans_list = self._db.select_ids(is_question_answer=True, is_intelligent=True)
            self.__intell__msg_list = self._db.select_ids(is_intelligent=True)

    @staticmethod
    def __captcha_handler(captcha):
        u"""
            При возникновении капчи вызывается эта функция и ей передается объект
            капчи. Через метод get_url можно получить ссылку на изображение.
            Через метод try_again можно попытаться отправить запрос с кодом капчи
        """

        key = input("Enter Captcha {0}: ".format(captcha.get_url())).strip()

        # Пробуем снова отправить запрос с капчей
        return captcha.try_again(key)

    def _add_msg_to_ignore(self, msg):
        u"""
            Добавляем в логгер сообщения, адресованные боту.
            Эти сообщения будут проигнорированы.
        """
        if 'chat_id' in msg:
            self._ignore_msgs.append('%s-%s-%s' % (msg['chat_id'], msg['id'], msg['user_id']))
        else:
            self._ignore_msgs.append('NONE-%s-%s' % (msg['id'], msg['user_id']))
        self._logger.write_history(self._ignore_msgs)

    def _is_msg_in_ignore(self, msg):
        u"""
            Проверяем есть ли сообщение в логгере.
            Если есть, то игнорим его.
        """
        # result = False
        if 'chat_id' in msg:
            result = '%s-%s-%s' % (msg['chat_id'], msg['id'], msg['user_id']) in self._ignore_msgs
        else:
            result = 'NONE-%s-%s' % (msg['id'], msg['user_id']) in self._ignore_msgs
        return result

    def _send(self, msg, text):
        u"""
            Метод отправки собщения с текстом text.
        """
        if 'chat_id' in msg:
            self._vk.messages.send(
                chat_id=msg['chat_id'],
                message=text
            )
        else:
            self._vk.messages.send(
                user_id=msg['user_id'],
                message=text
            )

    def _get_random_message(self, msg_list):
        u"""
            Получаем рандомное сообщение из списка айдишников сообщений.
        """
        if self._db:
            return self._db.get_message(random.choice(msg_list))
        else:
            return LITERALS['db_error']

    def _send_message_from_db(self, msg):
        u"""
            Метод отправляющий сообщение в чат с БД.
        """
        if '?' in msg['body']:
            text = self._get_random_message(self.__ans_list) if not self.__is_intelligent \
                else self._get_random_message(self.__intell__ans_list)
        else:
            text = self._get_random_message(self.__msg_list) if not self.__is_intelligent \
                else self._get_random_message(self.__intell__msg_list)
        self._send(msg, u'%s, %s' % (self._get_user_name(msg['user_id']), text))

    @staticmethod
    def _prepare_msg(msg):
        u"""
            Метод, используемый для подготовки сообщений для записи их в БД.
            Добавляет к спец. символам сообщения дополнительный слеш, с целью не потерять труктуру сообщения.
        """
        return msg.replace('\'', '\\\'')

    def _remember_new_data(self, msg):
        u"""
            Запись нового сообщения в БД, обновляем списки айдишников сообщений.
        """
        if self._db:
            self._db.add_new_row(
                msg['user_id'],
                self._prepare_msg(msg['body'][len(self._bot_name) + 9:]),
                is_intelligent=self.__is_intelligent
            )
            user_name = self._get_user_name(msg['user_id'])
            text = self._prepare_msg(msg['body'][len(self._bot_name) + 9:])
            self._send(
                msg,
                LITERALS['remember_data'].replace('{user_name}', user_name).replace('{message}', text)
            )
            print(u'Remember new data: from %s, msg: %s' % (msg['user_id'], text))
            self.__update_messages()

    def _forget_data(self, msg):
        u"""
            Помечаем сообщение как удаленое, обновляем списки айдишников сообщений.
        """
        if self._db:
            self._db.del_row(self._prepare_msg(msg['body'][len(self._bot_name) + 8:]))
            user_name = self._get_user_name(msg['user_id'])
            text = self._prepare_msg(msg['body'][len(self._bot_name) + 9:])
            self._send(
                msg,
                LITERALS['forget_data'].replace('{user_name}', user_name).replace('{message}', text)
            )
            print(u'Remove data: from %s, msg: %s' % (msg['user_id'], text))
            # self.__ans_list = self._db.select_ids()
            self.__update_messages()

    def _get_help(self):
        u"""
            Вывод справки по боту.
        """
        return emoji.emojize(u"""
:dizzy: Моя текущая версия: version

:book: Список моих команд на сегодня:
:small_red_triangle_down: Выучить что-то новое: name запомни <предложение/фраза>
:small_red_triangle_down: Выдать вероятность события: name инфа <фраза/название/событие>
:small_red_triangle_down: Выбирает случайного участника беседы: name кто <предложение/фраза>
:small_red_triangle_down: Сменить режим общения бота: name смени режим
:small_red_triangle_down: Получить текущий режим бота: name режим
:small_red_triangle_down: Получить список новостей: name новости
:small_red_triangle_down: Посчитать пример: name м
:small_red_triangle_down: Справка по математике: name м помощь
:small_red_triangle_down: Получить ТВ-программу на ближайшее время: name телепрограмма
:small_red_triangle_down: Просто попиздеть: name <предложение/фраза>
:star: [Для админов] Забыть что-то старое: name забудь <предложение/фраза>
:star: [Для админов] Выключить бота: name завали ебало
:star: [Для админов] Включить бота : name камбекнись

Список разработчиков:
:copyright: Илья - http://vk.com/id96996256
Список админов:
:a: Илья - http://vk.com/id96996256
:a: Дмитрий - http://vk.com/id77698338
:a: Полина - https://vk.com/id299314896
        """.replace('name', self._bot_name).replace('version', VERSION), use_aliases=True)

    def _get_bot_id(self):
        u"""
            Получаем айди вк бота.
        """
        return int(self._vk_session.token['user_id'])

    def _get_user_name(self, user_id):
        u"""
            Получаем имя пользователя по его айди.
        """
        return u'%s' % self._vk.users.get(user_ids=[user_id])[0]['first_name']

    def _get_user_lastname(self, user_id):
        u"""
            Получаем фамилию пользователя по его айди.
        """
        return u'%s' % self._vk.users.get(user_ids=[user_id])[0]['last_name']

    def _get_chat_users_ids(self, chat_id):
        u"""
            Получаем список пользователей чата по айдишнику чата.
        """
        users = self._vk.messages.getChatUsers(chat_id=chat_id)
        users.remove(self._get_bot_id())
        idx = random.randint(0, len(users) - 1)
        return u'%s %s' % (self._get_user_name(users[idx]), self._get_user_lastname(users[idx]))

    def __command_bot_off(self, msg):
        u"""
            Команда приостановления дейтельности бота.
        """
        if msg['body'][:len(self._bot_name) + 13] == LITERALS['commands']['bot_off']['cmd']\
                .replace('{bot_name}', self._bot_name):
            self._add_msg_to_ignore(msg)
            user_name = self._get_user_name(msg['user_id'])
            self._send(msg, LITERALS['commands']['bot_off']['answer'].replace('{user_name}', user_name))
            self.__disable = True
            return True
        return False

    def __command_bot_on(self, msg):
        u"""
            Команда возобновления дейтельности бота.
        """
        if msg['body'][:len(self._bot_name) + 13] == LITERALS['commands']['bot_on']['cmd']\
                .replace('{bot_name}', self._bot_name):
            self._add_msg_to_ignore(msg)
            user_name = self._get_user_name(msg['user_id'])
            self._send(msg, LITERALS['commands']['bot_on']['answer'].replace('{user_name}', user_name))
            self.__disable = False
            return True
        return False

    def __command_bot_help(self, msg):
        u"""
            Команда получения справки.
        """
        if msg['body'][:len(self._bot_name) + 8] == LITERALS['commands']['help']['cmd']\
                .replace('{bot_name}', self._bot_name):
            self._add_msg_to_ignore(msg)
            self._send(msg, '%s, %s' % (self._get_user_name(msg['user_id']), self._get_help()))
            return True
        return False

    def __command_bot_forget(self, msg):
        u"""
            Команда "удаления" сообщения бота.
        """
        if msg['body'][:len(self._bot_name) + 8] == LITERALS['commands']['forget']['cmd']\
                .replace('{bot_name}', self._bot_name):
            self._add_msg_to_ignore(msg)
            self._forget_data(msg)
            return True
        return False

    def __command_bot_remember(self, msg):
        u"""
            Команда, для запоминания сообщения.
        """
        if msg['body'][:len(self._bot_name) + 9] == LITERALS['commands']['remember']['cmd']\
                .replace('{bot_name}', self._bot_name):
            self._add_msg_to_ignore(msg)
            self._remember_new_data(msg)
            return True
        return False

    def __command_bot_probability(self, msg):
        u"""
            Команда получения процента.
        """
        if msg['body'][:len(self._bot_name) + 6] == LITERALS['commands']['probability']['cmd']\
                .replace('{bot_name}', self._bot_name):
            self._add_msg_to_ignore(msg)
            probability = random.randint(0, 100)
            if probability == 100:
                text = LITERALS['commands']['probability']['answer']['max'].replace('{percent}', str(probability))
            elif probability > 75:
                text = LITERALS['commands']['probability']['answer']['high'].replace('{percent}', str(probability))
            elif probability == 0:
                text = LITERALS['commands']['probability']['answer']['min'].replace('{percent}', str(probability))
            elif probability < 15:
                text = LITERALS['commands']['probability']['answer']['low'].replace('{percent}', str(probability))
            else:
                text = LITERALS['commands']['probability']['answer']['mid'].replace('{percent}', str(probability))
            self._send(msg, u'%s, %s' % (self._get_user_name(msg['user_id']), text))
            return True
        return False

    def __command_bot_message(self, msg):
        u"""
            Команда отправки ботом сообщения.
        """
        if msg['body'][:len(self._bot_name)] == self._bot_name \
                and not self._is_msg_in_ignore(msg) and len(msg['body']) > 5:
            self._add_msg_to_ignore(msg)
            self._send_message_from_db(msg)
            return True
        return False

    def __command_bot_change_mod(self, msg):
        u"""
            Команда смены режима общения бота.
        """
        if msg['body'][:len(self._bot_name) + 12] == LITERALS['commands']['change_mod']['cmd']\
                .replace('{bot_name}', self._bot_name):
            self._add_msg_to_ignore(msg)
            self.__is_intelligent = not self.__is_intelligent
            user_name = self._get_user_name(msg['user_id'])
            if self.__is_intelligent:
                text = LITERALS['commands']['change_mod']['answer']['intelligency'].replace('{user_name}', user_name)
            else:
                text = LITERALS['commands']['change_mod']['answer']['default'].replace('{user_name}', user_name)
            self._send(msg, text)
            return True
        return False

    def __command_bot_current_mod(self, msg):
        u"""
            Команда получения текущего режима общения.
        """
        if msg['body'][:len(self._bot_name) + 6] == LITERALS['commands']['current_mod']['cmd']\
                .replace('{bot_name}', self._bot_name):
            self._add_msg_to_ignore(msg)
            user_name = self._get_user_name(msg['user_id'])
            if self.__is_intelligent:
                text = LITERALS['commands']['current_mod']['answer']['intelligency'].replace('{user_name}', user_name)
            else:
                text = LITERALS['commands']['current_mod']['answer']['default'].replace('{user_name}', user_name)
            self._send(msg, text)
            return True
        return False

    def __command_bot_news(self, msg):
        u"""
            Команда получения актуальных новостей по РФ и СПб с сайта http://yandex.ru.
        """
        if msg['body'][:len(self._bot_name) + 8] == LITERALS['commands']['news']['cmd']\
                .replace('{bot_name}', self._bot_name):
            self._add_msg_to_ignore(msg)
            self._send(msg, u'%s,\n%s' % (self._get_user_name(msg['user_id']), self._news.get_news()))
            return True
        return False

    def __command_bot_tv_list(self, msg):
        u"""
           Команда получения актуальной телепрограммы с сайта http://yandex.ru.
        """
        if msg['body'][:len(self._bot_name) + 14] == LITERALS['commands']['tv_list']['cmd']\
                .replace('{bot_name}', self._bot_name):
            self._add_msg_to_ignore(msg)
            self._send(msg, u'%s,\n%s' % (self._get_user_name(msg['user_id']), self._news.get_tv_list()))
            return True
        return False

    def __command_bot_math(self, msg):
        u"""
            Команда для вычисления математических выражений.
         """
        if msg['body'][:len(self._bot_name) + 9] == LITERALS['commands']['math']['cmd']['help']\
                .replace('{bot_name}', self._bot_name):
            self._add_msg_to_ignore(msg)
            user_name = self._get_user_name(msg['user_id'])
            help_text = self._math.get_help()
            self._send(
                msg,
                LITERALS['commands']['math']['answer'].replace('{user_name}', user_name).replace('{help}', help_text)
            )
            return True

        if msg['body'][:len(self._bot_name) + 3] == LITERALS['commands']['math']['cmd']['calc']\
                .replace('{bot_name}', self._bot_name):
            self._add_msg_to_ignore(msg)
            self._send(msg, u'%s, %s' % (
                self._get_user_name(msg['user_id']),
                self._math.calculate(msg['body'][len(self._bot_name) + 3:])
            ))
            return True
        return False

    def __command_bot_who_is(self, msg):
        u"""
            Команда вывода ответа на вопрос "кто ...?"
         """
        if 'chat_id' in msg:
            if msg['body'][:len(self._bot_name) + 4] == LITERALS['commands']['who_is']['cmd']\
                    .replace('{bot_name}', self._bot_name):
                self._add_msg_to_ignore(msg)
                user_name = self._get_chat_users_ids(msg['chat_id'])
                answer = LITERALS['commands']['who_is']['answer']
                self._send(msg, u'%s, %s' % (
                    self._get_user_name(msg['user_id']),
                    answer[random.randint(0, len(answer) - 1)].replace('{user_name}', user_name)
                ))
                return True
        return False

    def __analyze_messages(self, msg_list=None):
        u"""
            Основной метод анализа входящих сообщений.
            Бот анализирует только те сообщения, которые адресованы именно ему.
            Анализ идет исходя из правил русского языка: "ИмяБота[,] текст сообщения"
         """
        if msg_list:
            for msg in msg_list:
                if not self._is_msg_in_ignore(msg):
                    if not self.__disable:
                        if msg['user_id'] in ADMIN_LIST:
                            self.__command_bot_off(msg)
                            self.__command_bot_forget(msg)

                        self.__command_bot_help(msg)
                        self.__command_bot_remember(msg)
                        self.__command_bot_probability(msg)
                        self.__command_bot_change_mod(msg)
                        self.__command_bot_current_mod(msg)
                        self.__command_bot_news(msg)
                        self.__command_bot_tv_list(msg)
                        self.__command_bot_math(msg)
                        self.__command_bot_who_is(msg)
                        # априори последняя команда, иначе все что после выполнено не будет.
                        self.__command_bot_message(msg)
                    else:
                        if msg['user_id'] in ADMIN_LIST:
                            self.__command_bot_on(msg)

    def __main(self):
        u"""
            Основной метод бота для работы.
            Читает первые 5 входящих сообщений.
         """
        while True:
            self.__analyze_messages(self._vk.messages.get(count=5)['items'])
            # current_chat_title = vk.messages.getChat(chat_id=target_chat_id)['title']
            # if current_chat_title != target_chat_title:
            #     print('Changed:', current_chat_title, 'to', target_chat_title)
            #     vk.messages.editChat(chat_id=target_chat_id, title=target_chat_title)
            time.sleep(2)

    def start_bot(self, debug=False):
        u"""
            Метод, запускающий бота.
         """
        print(u"Starting work...")
        while True:
            if debug:
                self.__main()
            else:
                try:
                    self.__main()
                except Exception as error_msg:
                    print('Oops! I\'m restarting. Error: %s' % error_msg)
