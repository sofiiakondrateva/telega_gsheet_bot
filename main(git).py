#!/usr/bin/env python
# coding: utf-8

# In[1]:


from flask import Flask
from flask import request
from flask_sslify import SSLify
import re
import gspread
from datetime import datetime, time
from oauth2client.service_account import ServiceAccountCredentials


# In[2]:


token = '***' #токен бота

CREDENTIALS_FILE = '*****.json'  # Имя файла с закрытым ключом
credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])


# In[3]:


app = Flask(__name__)
sslify = SSLify(app)


# In[17]:


# Авторизовываемся и открываем таблицы
gc = gspread.authorize(credentials)
backup_spreadsheet = gc.open('Monitoring-bot')
mrt_spreadsheet = gc.open('Мониторинг рисковых тем') # изменить!!!!!!!!!!!!


# In[1]:


def next_available_row_socmedia(wks):
    str_list = list(filter(None, wks.col_values(8)))  # fastest
    return str(len(str_list)+1)


# In[3]:


def next_available_row_smi(wks):
    str_list = list(filter(None, wks.col_values(7)))  # fastest
    return str(len(str_list)+1)


# In[5]:


# Парсим update_id
def get_update_id(update):
    return update['update_id']


# In[6]:


### Парсим дату и время появления в Дежурке
def get_date(update):
    dt_object = datetime.fromtimestamp(update['channel_post']['date']) #дата попадания в дежурку
    date_str = dt_object.strftime("%Y-%m-%d %H:%M:%S")
    return date_str


# In[7]:


# Парсим медиа груп ид (складывать в бэкап)
def get_media_group_id(update):
    if 'media_group_id' in update['channel_post']:
        return update['channel_post']['media_group_id']
    else:
        return None


# In[8]:


#Маргарита, Ульяна, все тексты
def parse_link_from_text_field(update):
    for text in re.split('\n| ', update['channel_post']['text']):
        if 'http' in text:
            return text


# In[9]:


# Ссылка на все каналы, из которых есть форвард без ссылки на первоисточник
def parse_link_forward_channel(update):
    return 'https://t.me/'+ update['channel_post']['forward_from_chat']['username']+ '/'+ str(update['channel_post']['forward_from_message_id'])


# In[10]:


# Ссылка на Дежурку, если нет ссылок ни на что
def parse_link_from_dezhurka(update):
    return 'https://t.me/c/1446288415/'+ str(update['channel_post']['message_id'])


# In[11]:


def parse_link_from_url_field(update):
    for every_ent in update['channel_post']['entities']:
        if 'url' in every_ent:
            return every_ent['url']


# In[12]:


# подписи к фото Captions
def parse_link_from_caption(update):
    for text in re.split('\n| ', update['channel_post']['caption']):
        if 'http' in text:
            return text


# In[13]:


def parse_links(update):
    try:
        if 'entities' in update['channel_post']:
            try:
                if 'forward_from_chat' in update['channel_post']:
                    return(parse_link_forward_channel(update))
                elif parse_link_from_url_field(update) == None:
                    return(parse_link_from_text_field(update))
                else:
                    return(parse_link_from_url_field(update))
            except:
                return(parse_link_from_text_field(update))
        else:
            if 'caption' in update['channel_post']:
                if parse_link_from_caption(update) == None:
                    return(parse_link_forward_channel(update))
                else:
                    return(parse_link_from_caption(update))  #тут проверить, если сам постишь картинку с подписью, то что
            elif 'forward_from_chat' in update['channel_post']:
                return(parse_link_forward_channel(update))

            else:
                return(parse_link_from_dezhurka(update))
    except:
        return('Бот не нашел ссылку')


# In[14]:


#Дебаг
def type_link(link):
    try:
        if 'facebook' in link or 'local.yandex' in link or 't.me' in link or 'vk.com' in link or 'twitter.com' in link or 'telegram.me' in link or 'instagram.com' in link or 'ok.ru' in link or 'youtube.com' in link or 'youtu.be' in link or 't.co' in link or 'zen.yandex' in link or 'livejournal.com' in link:
            return 'Социальные сети', link
        else:
            return 'СМИ', link
    except:
        pass


# In[15]:


# Грузим данные в backup (Monitoring-bot)
def upload_to_backup_spreadsheet(link_and_type, date, update_id, media_group_id):
    try:
        if link_and_type[0] == 'Социальные сети':
            backup_spreadsheet.worksheet('Социальные сети').append_row([link_and_type[1],date, update_id, media_group_id])
        else:
            backup_spreadsheet.worksheet('СМИ').append_row([link_and_type[1],date, update_id, media_group_id])
    except:
        pass


# In[2]:


# Грузим данные в  Моинторинг рисковых тем
def upload_to_mrt_spreadsheet(link_and_type, date):
    try:
        if link_and_type[0] == 'Социальные сети':
            next_row = next_available_row_socmedia(mrt_spreadsheet.worksheet('Социальные сети'))
            mrt_spreadsheet.worksheet('Социальные сети').update_acell("H{}".format(next_row),link_and_type[1])
            mrt_spreadsheet.worksheet('Социальные сети').update_acell("A{}".format(next_row),date)
        else:
            next_row = next_available_row_smi(mrt_spreadsheet.worksheet('СМИ'))
            mrt_spreadsheet.worksheet('СМИ').update_acell("G{}".format(next_row),link_and_type[1])
            mrt_spreadsheet.worksheet('СМИ').update_acell("A{}".format(next_row),date)
    except:
        pass


# In[ ]:


@app.route('/***', methods=['POST', 'GET']) #токен бота
def index():
    if request.method == 'POST':
        try:
            update = request.get_json()
            link = parse_links(update)
            link_and_type = type_link(link)
            date = get_date(update)
            update_id = get_update_id(update)
            media_group_id = get_media_group_id(update)
            if backup_spreadsheet.worksheet('Социальные сети').col_values(4)[-1] == media_group_id and backup_spreadsheet.worksheet('Социальные сети').col_values(4)[-1] != None:
                pass
            else:
                upload_to_backup_spreadsheet(link_and_type, date, update_id, media_group_id)
                upload_to_mrt_spreadsheet(link_and_type, date)
        except:
            pass
    return '<h1>Bot welcomes you</h1>'


# In[ ]:


#if __name__ == '__main__':
#    app.run()
