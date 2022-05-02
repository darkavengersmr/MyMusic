#!/usr/bin/python3

import asyncio
import motor.motor_asyncio

from config import DBSOCKET, USER

from db_module import next_track, update_now_play

loop = asyncio.get_event_loop()

db_client = motor.motor_asyncio.AsyncIOMotorClient(f'mongodb://{DBSOCKET}', io_loop=asyncio.get_event_loop())
db = db_client.my_music
my_music_collection = db.my_music

track = loop.run_until_complete(next_track(my_music_collection))
loop.run_until_complete(update_now_play(my_music_collection, USER, track))
print(track)
