# Система должна за последние 15 минут проверять на аномалии ключевые метрики, такие как активные пользователи
# в ленте / мессенджере, просмотры, лайки, CTR, количество отправленных сообщений.

# Для проверки на аномалии используется правило сигм (по умолчанию – 3 сигм).
# Сообщения отправляются в случае, если за последние (уже прошедшие) 15 минут были аномалии.

import numpy as np
import telegram as tl
from CH import Getch
from datetime import timedelta
import os


# 1. Класс метрики
# Включает в себя структуру (само значение метрики; название, соответствующая ссылка на чарт,
# имя ответственного в телеграме, название сервиса – для вывода информации о метрике).
# Также содержит метод для обнаружения аномалий для метрики

class Metric():

    def __init__(self, metric, name, link, responsible, source):
        self.value = metric
        self.name = name
        self.link = link
        self.responsible = responsible
        if source == 'feed':
            self.source = 'лента новостей'
        else:
            self.source = 'мессенджер'

    def check_anomaly(self, bot, chat_id, a=3):
        mean_metric = self.value[:-1].mean()
        std_metric = self.value[:-1].std()
        dif = self.value[-1] - mean_metric
        if (self.value[-1] > mean_metric + a * std_metric) or (self.value[-1] < mean_metric - a * std_metric):
            bot.sendMessage(chat_id=chat_id, parse_mode='markdown',
                            text='*Найдена аномалия* за предыдущие 15 минут для метрики\n «{}»:\n'
                                 '\n'
                                 '– Сервис: {}\n'
                                 '– Период:    {}   –   {}\n'
                                 '– Значение метрики: {}\n'
                                 '– Отклонение от среднего значения за неделю: {} ({}% от среднего)\n'
                                 '– Ссылка на чарт: {}\n'
                                 '\n'
                                 '{}, посмотри, пожалуйста\n'
                            .format(self.name, self.source, self.value.index[-1],
                                    self.value.index[-1] + timedelta(minutes=15), np.round(self.value[-1], 2),
                                    np.round(dif, 2), np.abs(np.round(dif*100/mean_metric, 1)), self.link,
                                    self.responsible))


def run_alerts(chat=None):

    # 2. Переменные бота и чата

    bot = tl.Bot(token=os.environ.get("Report_Bot_Token"))
    chat_id = os.environ.get("Anomalies_Chat_Id")

    # 3. Выгрузка нужного среза данных

    query_last_week_feed = 'select user_id, toStartOfFifteenMinutes(time) as ts, action ' \
                           'from simulator_20220120.feed_actions ' \
                           'where toDate(time) <= today() and toDate(time) >= today() - interval 7 day ' \
                           'and toTime(toStartOfFifteenMinutes(time)) = ' \
                           'toTime(toStartOfFifteenMinutes(now()) - interval 15 minute) ' \
                           'order by ts'
    data_last_week_feed = Getch(query_last_week_feed).df

    query_last_week_messenger = 'select user_id, toStartOfFifteenMinutes(time) as ts ' \
                                'from simulator_20220120.message_actions ' \
                                'where toDate(time) <= today() and toDate(time) >= today() - interval 7 day ' \
                                'and toTime(toStartOfFifteenMinutes(time)) = ' \
                                'toTime(toStartOfFifteenMinutes(now()) - interval 15 minute) ' \
                                'order by ts'
    data_last_week_messenger = Getch(query_last_week_messenger).df

    # 4. Расчет метрик

    # 4.1 Активные пользователи

    active_users_last_week_feed = data_last_week_feed.user_id.groupby(data_last_week_feed.ts).nunique()
    active_users_feed = Metric(active_users_last_week_feed, 'Активные пользователи',
                               'http://superset.lab.karpov.courses/r/505',
                               '@ActiveUsersResponsible', 'feed')

    active_users_last_week_messenger = data_last_week_messenger.user_id.groupby(data_last_week_messenger.ts).nunique()
    active_users_messenger = Metric(active_users_last_week_messenger, 'Активные пользователи',
                                    'http://superset.lab.karpov.courses/r/506',
                                    '@ActiveUsersResponsible', 'messenger')

    # 4.2 Лайки, Просмотры, Сообщения, CTR (лайки к просмотрам)

    likes_last_week = data_last_week_feed.loc[data_last_week_feed.action == 'like', 'action']. \
        groupby(data_last_week_feed.ts).count()
    likes = Metric(likes_last_week, 'Лайки', 'http://superset.lab.karpov.courses/r/507', '@LikesResponsible', 'feed')

    views_last_week = data_last_week_feed.loc[data_last_week_feed.action == 'view', 'action']. \
        groupby(data_last_week_feed.ts).count()
    views = Metric(views_last_week, 'Просмотры', 'http://superset.lab.karpov.courses/r/508', '@ViewsResponsible',
                   'feed')

    messages_last_week = data_last_week_messenger.user_id.groupby(data_last_week_messenger.ts).count()
    messages = Metric(messages_last_week, 'Отправленные сообщения', 'http://superset.lab.karpov.courses/r/509',
                      '@MessagesResponsible', 'messenger')

    CTR_feed_last_week = likes_last_week / views_last_week
    CTR_feed = Metric(CTR_feed_last_week, 'CTR (Лайки к просмотрам)', 'http://superset.lab.karpov.courses/r/510',
                      '@CTRResponsible', 'feed')

    # 5. Запуск проверки на аномалии

    active_users_feed.check_anomaly(bot, chat_id)
    active_users_messenger.check_anomaly(bot, chat_id)
    likes.check_anomaly(bot, chat_id)
    views.check_anomaly(bot, chat_id)
    messages.check_anomaly(bot, chat_id)
    CTR_feed.check_anomaly(bot, chat_id)

    print(CTR_feed_last_week)
    mean_DAU = CTR_feed_last_week.mean()
    print(mean_DAU)
    std_DAU = CTR_feed_last_week.std()
    print(std_DAU)


try:
    run_alerts()
except Exception as e:
    print(e)
