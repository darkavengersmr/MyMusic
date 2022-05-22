#!/usr/bin/python3

import datetime
import ast
import requests
import sys
from tinytag import TinyTag

import asyncio
import motor.motor_asyncio

from config import DBSOCKET

from db_module import next_track, update_now_play, get_credentials, discrement_user_active, user_is_active, \
    get_prev_track, add_to_history

loop = asyncio.get_event_loop()

db_client = motor.motor_asyncio.AsyncIOMotorClient(f'mongodb://{DBSOCKET}', io_loop=asyncio.get_event_loop())
db = db_client.my_music
my_music_collection = db.music
my_music_settings = db.settings

# выясняем пользователя, которому нужно поставить трек
user = sys.argv[0][sys.argv[0].find("_")+1:len(sys.argv[0])-3]

# смотрим нужно ли переходить к предыдущему треку
track = loop.run_until_complete(get_prev_track(user))
if not track:
    # получаем следующий трек для пользователя по его предпочтениям
    track = loop.run_until_complete(next_track(user, collection=my_music_collection))

# читаем из трека метаинформацию
tag = TinyTag.get(track['fullname'].rstrip())
tags = {
    'artist': tag.artist,
    'album': tag.album,
    'title': tag.title,
    'genre': tag.genre,
    'year': tag.year
}

# пишем в профиль пользователя какой трек сейчас будем запускать
loop.run_until_complete(update_now_play(my_music_settings, user, track['fullname'], tags))

# пишем историю
loop.run_until_complete(add_to_history(user, tags))

# Отправляем на Rest метаинформацию (исполнитель, название) о треке, который будем запускать
credentials = loop.run_until_complete(get_credentials())
if user in credentials:
    password = credentials[user]

    data = {'username': user, 'password': password}
    response = requests.post('http://localhost:8000/auth', data=data)

    dict_str = response.content.decode("UTF-8")
    mydata = ast.literal_eval(dict_str)

    headers = {"Authorization": f"Bearer {mydata['access_token']}"}
    params = {"now_play": f"{tag.artist} - {tag.title}"}
    requests.post('http://localhost:8000/now_play', headers=headers, params=params)

# возвращаем трек, который нужно запустить
print(track['fullname'])

loop.run_until_complete(discrement_user_active(user))


def stop_streaming_to_user(this_user, this_credentials):
    this_password = this_credentials[this_user]
    socket = 'http://localhost:8000'
    data = {'username': this_user, 'password': this_password}
    response = requests.post(f'{socket}/auth', data=data)

    dict_str = response.content.decode("UTF-8")
    mydata = ast.literal_eval(dict_str)

    headers = {"Authorization": f"Bearer {mydata['access_token']}"}
    params = {"operation": "stop"}
    requests.get(f'{socket}/playback', headers=headers, params=params)


# отключаем пользователя по неактивности
user_active = loop.run_until_complete(user_is_active(user))
if not user_active:
    stop_streaming_to_user(user, credentials)


# отключение всех пользователей по времени ночью
date = datetime.datetime.today()
if date.strftime('%H') == '03':
    for u in credentials:
        stop_streaming_to_user(u, credentials)
