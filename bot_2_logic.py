import numpy as np
import telegram as tl
import matplotlib.pyplot as plt
import seaborn as sns
import io
from CH import Getch
import pandas as pd
from telegram import InputMediaPhoto
import os


#  1. Функция для создания графиков

def build_plot(title, file_name, metric1, metric2=pd.DataFrame(),  legend='', metric3=pd.DataFrame()):
    plt.figure(figsize=(9, 6))
    plt.title(title)
    plt.xlabel('Дата')
    plt.ylabel('Величина')
    for tick in sns.lineplot(data=metric1, marker='o', color='darkmagenta').get_xticklabels():
        tick.set_rotation(30)
    if not metric2.empty:
        sns.lineplot(data=metric2, marker='o')
    if not metric3.empty:
        sns.lineplot(data=metric3, marker='o')
    plt.legend(legend)
    plot_object = io.BytesIO()
    plt.savefig(plot_object)
    plot_object.seek(0)
    plot_object.name = file_name
    return plot_object


# 2. Расчет аудиторных метрик за прошлую неделю

# 2.1. Выгрузка нужного среза данных

# 2.1.1 Из ленты новостей

query_last_week_feed = "SELECT user_id, toDate(time) as date, action FROM simulator_20220120.feed_actions " \
                       "WHERE toDate(time) < today() AND toDate(time) >= today() - interval 7 day " \
                       "ORDER BY date"
data_last_week_feed = Getch(query_last_week_feed).df

# 2.1.2 Из мессенджера

query_last_week_messanger = "select user_id, toDate(time) as date, 'message' as action " \
                            "from simulator_20220120.message_actions " \
                            'where toDate(time) < today() and toDate(time) >= today() - interval 7 day ' \
                            'order by date'
data_last_week_messanger = Getch(query_last_week_messanger).df

# 2.1.3 Объединение (inner) ленты новостей и мессенджера

data_inner = pd.merge(data_last_week_feed, data_last_week_messanger, how='inner',
                      left_on=['user_id', 'date'], right_on=['user_id', 'date'])

# 2.2 Расчет метрик

# 2.2.1 DAU ленты и мессенджера

DAU_last_week_feed = data_last_week_feed.groupby(data_last_week_feed.date).user_id.nunique()
DAU_last_week_messanger = data_last_week_messanger.groupby(data_last_week_messanger.date).user_id.nunique()

actions_feed_views = data_last_week_feed.loc[data_last_week_feed.action == 'view', 'action'].\
    groupby(data_last_week_feed.date).count()
actions_feed_likes = data_last_week_feed.loc[data_last_week_feed.action == 'like', 'action'].\
    groupby(data_last_week_feed.date).count()
actions_messanger = data_last_week_messanger.action.\
    groupby(data_last_week_messanger.date).count()

# 2.2.2 Кол-во действий на пользователя

actions_feed_views_per_user = data_last_week_feed.loc[data_last_week_feed.action == 'view', 'action'].\
    groupby(data_last_week_feed.date).count()/data_last_week_feed.loc[data_last_week_feed.action == 'view', 'user_id'].\
    groupby(data_last_week_feed.date).nunique()

actions_feed_likes_per_user = data_last_week_feed.loc[data_last_week_feed.action == 'like', 'action'].\
    groupby(data_last_week_feed.date).count()/data_last_week_feed.loc[data_last_week_feed.action == 'like', 'user_id'].\
    groupby(data_last_week_feed.date).nunique()

actions_messages_per_user = data_last_week_messanger.action.\
    groupby(data_last_week_messanger.date).count()/data_last_week_messanger.user_id.\
    groupby(data_last_week_messanger.date).nunique()

# 2.2.3 DAU (пользователи мессенджера и те, кто использует и мессенджер, и ленту)

unique_users_messanger = data_last_week_feed.groupby(data_last_week_messanger.date).user_id.nunique()
unique_users_inner = data_inner.groupby(data_inner.date).user_id.nunique()


# 3. Переменные бота и чата

bot = tl.Bot(token=os.environ.get("Report_Bot_Token"))
chat_id = os.environ.get("Reports_Chat_Id")


# 4. Отправка аудиторных метрик за вчера в чат

bot.sendMessage(chat_id=chat_id,
                text='Метрики за вчера:\n'
                     '\n'
                     '– DAU:\n'
                     '   • Лента новостей – {}\n'
                     '   • Мессенджер – {}\n'
                     '   • Лента новостей и мессенджер одновременно – {}\n'
                     '– Действия пользователей:\n'
                     '   • Всего – {}\n'
                     '   • Просмотры – {}\n'
                     '   • Лайки – {}\n'
                     '   • Сообщения – {}\n'
                     '– Усредненное кол-во действий на пользователя:\n'
                     '   • Всего – {}\n'
                     '   • Просмотры – {}\n'
                     '   • Лайки – {}\n'
                     '   • Сообщения – {}\n'
                     '\n'
.format(DAU_last_week_feed.iloc[-1], DAU_last_week_messanger.iloc[-1], unique_users_inner.iloc[-1],
        actions_feed_views.iloc[-1] + actions_feed_likes.iloc[-1] + actions_messanger.iloc[-1],
        actions_feed_views.iloc[-1], actions_feed_likes.iloc[-1], actions_messanger.iloc[-1],
        round(actions_feed_views_per_user.iloc[-1] + actions_feed_likes_per_user.iloc[-1] + actions_messages_per_user.iloc[-1]),
        round(actions_feed_views_per_user.iloc[-1]), round(actions_feed_likes_per_user.iloc[-1]),
        round(actions_messages_per_user.iloc[-1])))


# 5. Создание объектов графиков с аудиторными метриками за прошлую неделю

sns.set()

DAU_object = build_plot('DAU', 'DAU_plot.png', DAU_last_week_feed, DAU_last_week_messanger,
                        ('Пользователи ленты новостей', 'Пользователи мессенджера'))
metrics_object = build_plot('Действия пользователей', 'metrics_plot.png',
                            actions_feed_views, actions_feed_likes,
                            ('Просмотры', 'Лайки', 'Сообщения'), actions_messanger)

inner_object = build_plot('DAU (пользователи мессенджера и те, кто использует и мессенджер, и ленту)',
                          'DAU_inner_plot.png', unique_users_messanger, unique_users_inner,
                          ('Используют мессенджер', 'Используют мессенджер и ленту'))

actions_per_user_object = build_plot('Усредненное кол-во действий на пользователя', 'DAU_inner_plot.png',
                                     actions_feed_views_per_user, actions_feed_likes_per_user,
                                     ('Просмотры', 'Лайки', 'Сообщения'), actions_messages_per_user)


# 6. Отправка графиков в чат

bot.sendMediaGroup(chat_id=chat_id, media=[InputMediaPhoto(DAU_object, caption="Метрики за прошлую неделю"),
                                           InputMediaPhoto(inner_object),
                                           InputMediaPhoto(metrics_object),
                                           InputMediaPhoto(actions_per_user_object)])
