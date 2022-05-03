#!/usr/bin/python3

import asyncio
import motor.motor_asyncio
from tinytag import TinyTag

from config import DBSOCKET

db_client = motor.motor_asyncio.AsyncIOMotorClient(f'mongodb://{DBSOCKET}')
db = db_client.my_music
my_music_collection = db.music
my_music_settings = db.settings


async def do_insert_one(collection, document):
    result = await collection.insert_one(document)
    return result.inserted_id


async def do_insert_many(collection, documents):
    result = await collection.insert_many(documents)
    return result.inserted_ids


async def do_delete_many(collection):
    result = await collection.delete_many({})
    return result


async def next_track(collection):
    res_random = collection.aggregate([{"$match": {"fullname": { "$exists" : True }}},
                                      {"$sample": {"size": 1}}])
    res = []
    async for el in res_random:
        res.append(el)
    return res[0]


async def add_to_db(collection, playlist):
    documents = []
    with open(playlist, "r") as my_playlist:
        i = 0
        for file in my_playlist:
            try:
                tag = TinyTag.get(file.rstrip())
                tags = {
                    'artist': tag.artist,
                    'album': tag.album,
                    'title': tag.title,
                    'genre': tag.genre
                }
                i += 1
                if (i % 1000 == 0):
                    print(i)
                documents.append({'fullname': file, **tags})
            except:
                pass

    await do_insert_many(collection, documents)


async def update_now_play(collection, user, track, tags):
    if await collection.find_one({user: {"$exists": True}}):
        await collection.replace_one({user: {"$exists": True}},
                                     {user: {'last_track': {'fullname': track, **tags}}}, True)
    else:
        await collection.insert_one({user: {'last_track': {'fullname': track, **tags}}})


async def get_credentials():
    res = await my_music_settings.find_one({"login": {"$exists": True }})
    return res["login"]


async def get_top_genres(limit: int = 500):
    res_all = list(await my_music_collection.distinct("genre"))
    res = []
    for el in res_all:
        num = await my_music_collection.count_documents({"genre": el})
        if num > limit and el is not None:
            res.append(el)
    return res


async def get_artists_by_genres(genre: str, limit: int = 20):
    res_all = list(await my_music_collection.find({"genre": genre}).distinct("artist"))
    res = []
    for el in res_all:
        num = await my_music_collection.count_documents({"artist": el})
        if num > limit and el is not None:
            res.append(el)
    return res