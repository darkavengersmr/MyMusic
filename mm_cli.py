#!/usr/bin/python3

import os
import sys
import argparse

import asyncio
import motor.motor_asyncio

from config import DBSOCKET

from db_module import do_delete_many, add_to_db

loop = asyncio.get_event_loop()

db_client = motor.motor_asyncio.AsyncIOMotorClient(f'mongodb://{DBSOCKET}', io_loop=asyncio.get_event_loop())
db = db_client.my_music
my_music_collection = db.my_music


def createParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--add', default=None)
    parser.add_argument('-c', '--clear', default=None)
    parser.add_argument('-p', '--path', default=None)
    return parser


parser = createParser()
namespace = parser.parse_args(sys.argv[1:])

if namespace.add is None and namespace.clear is None:
    print('Please specify operation (add/clear db) or see help (-h)')
    sys.exit()

if namespace.path is None and namespace.add is not None:
    print('Please specify full path or see help (-h)')
    sys.exit()

if namespace.clear is not None:
    answer = input("Really clean DB? (y/n): ")
    if answer == "y" or answer == "Y":
        loop.run_until_complete(do_delete_many(my_music_collection))
        print(f'Database is cleared')
    else:
        sys.exit()

if namespace.add is not None:
    playlist = "playlist.txt"
    os.system(f"find {namespace.path} -name '*.mp3' >{playlist}")
    loop.run_until_complete(add_to_db(my_music_collection, playlist))
    print(f'New music added')


