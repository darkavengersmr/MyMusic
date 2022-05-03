#!/usr/bin/python3

import sys
from tinytag import TinyTag

import asyncio
import motor.motor_asyncio

from config import DBSOCKET

from db_module import next_track, update_now_play

db_client = motor.motor_asyncio.AsyncIOMotorClient(f'mongodb://{DBSOCKET}')
db = db_client.my_music
my_music_collection = db.music
my_music_settings = db.settings

track = asyncio.run(next_track(my_music_collection))

tag = TinyTag.get(track['fullname'].rstrip())
tags = {
    'artist': tag.artist,
    'album': tag.album,
    'title': tag.title,
    'genre': tag.genre
}

user = sys.argv[0][sys.argv[0].find("_")+1:len(sys.argv[0])-3]
asyncio.run(update_now_play(my_music_settings, user, track['fullname'], tags))

print(track['fullname'])
