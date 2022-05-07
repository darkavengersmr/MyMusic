#!/usr/bin/python3

import sys
from tinytag import TinyTag

import asyncio
import motor.motor_asyncio

from config import DBSOCKET

from db_module import next_track, update_now_play

loop = asyncio.get_event_loop()

db_client = motor.motor_asyncio.AsyncIOMotorClient(f'mongodb://{DBSOCKET}', io_loop=asyncio.get_event_loop())
db = db_client.my_music
my_music_collection = db.music
my_music_settings = db.settings

user = sys.argv[0][sys.argv[0].find("_")+1:len(sys.argv[0])-3]

track = loop.run_until_complete(next_track(user, collection=my_music_collection))

tag = TinyTag.get(track['fullname'].rstrip())
tags = {
    'artist': tag.artist,
    'album': tag.album,
    'title': tag.title,
    'genre': tag.genre,
    'year': tag.year
}

loop.run_until_complete(update_now_play(my_music_settings, user, track['fullname'], tags))

print(track['fullname'])
