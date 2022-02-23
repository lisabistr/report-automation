import numpy as np
import telegram as tl
import matplotlib.pyplot as plt
import seaborn as sns
import io
from CH import Getch
import pandas as pd
from datetime import date, timedelta
import os


#  1. Функция для создания графиков

def build_plot(title, metric1, metric2=pd.DataFrame()):
    plt.title(title)
    plt.xlabel('Дата')
    plt.ylabel('Величина')
    for tick in sns.lineplot(data=metric1, marker='o', color='darkmagenta').get_xticklabels():
        tick.set_rotation(30)
    if not metric2.empty:
        sns.lineplot(data=metric2, marker='o')
        plt.legend(('Просмотры', 'Лайки'))


# 2. Расчет аудиторных метрик за прошлую неделю

# 2.1. Выгрузка нужного среза данных
query_last_week = 'select user_id, time, action from simulator_20220120.feed_actions ' \
                  'where toDate(time) < today() and toDate(time) >= today() - interval 7 day ' \
                  'order by time'

data_last_week = Getch(query_last_week).df

# 2.2 Расчет метрик

DAU_last_week = data_last_week.groupby(data_last_week.time.dt.date).user_id.nunique()
views_last_week = data_last_week.loc[data_last_week.action == 'view', 'action'].\
    groupby(data_last_week.time.dt.date).count()
likes_last_week = data_last_week.loc[data_last_week.action == 'like', 'action'].\
    groupby(data_last_week.time.dt.date).count()
CTR_last_week = likes_last_week / views_last_week


# 3. Расчет аудиторных метрик за вчера

# 3.1 Отсекание нужного среза данных от данных за неделю

data_yesterday = data_last_week[data_last_week.time.dt.date == date.today() - timedelta(days=1)]

# 3.2 Расчет метрик
DAU_yesterday = data_yesterday.user_id.nunique()
views_yesterday = data_yesterday.action[data_yesterday.action == 'view'].count()
likes_yesterday = data_yesterday.action[data_yesterday.action == 'like'].count()
if views_yesterday != 0:
    CTR_yesterday = likes_yesterday/views_yesterday
else:
    CTR_yesterday = -1


# 4. Переменные бота и чата

bot = tl.Bot(token=os.environ.get("Report_Bot_Token"))
chat_id = os.environ.get("Reports_Chat_Id")

# 5. Отправка аудиторных метрик за вчера в чат

bot.sendMessage(chat_id=chat_id,
                text='Метрики за вчера:\n'
                     '– DAU: {}\n'
                     '– Просмотры: {}\n'
                     '– Лайки: {}\n'
                     '– CTR: {}'.format(DAU_yesterday, views_yesterday, likes_yesterday,
                                        np.round(CTR_yesterday, decimals=3)))

# 6. Создание объектов графиков с аудиторными метриками за прошлую неделю

sns.set()
plt.figure(figsize=(12, 15))
plt.subplot(2, 2, 1)
build_plot('DAU', DAU_last_week)
plt.subplot(2, 2, 2)
build_plot('Просмотры и лайки', views_last_week, likes_last_week)
plt.subplot(2, 1, 2)
build_plot('CTR (лайки к просмотрам)', CTR_last_week)
plt.suptitle('Метрики за прошлую неделю')
plot_object = io.BytesIO()
plt.savefig(plot_object)
plot_object.name = 'plots_last_week.png'
plot_object.seek(0)


# 7. Отправка графиков в чат

bot.sendPhoto(chat_id=chat_id, photo=plot_object)
