#!/usr/bin/python3

import datetime
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


async def get_filters(user, collection=my_music_settings):
    settings = await collection.find_one({user: {"$exists": True}})
    if settings and 'filter' in settings:
        return settings['filter']
    else:
        return {'mode': None, 'genre': None, 'artist': None, 'year': None}


async def next_track(user, collection=my_music_collection):
    filters = await get_filters(user, collection=my_music_settings)
    res_random = []
    if filters['mode'] == 'genre' and filters["genre"] is not None:
        res_random = collection.aggregate([{"$match": {"genre": f'{filters["genre"]}'}},
                                           {"$sample": {"size": 1}}])
    elif filters['mode'] == 'artist' and filters["artist"] is not None:
        res_random = collection.aggregate([{"$match": {"artist": f'{filters["artist"]}'}},
                                           {"$sample": {"size": 1}}])
    elif filters['mode'] == 'year' and filters["year"] is not None:
        res_random = collection.aggregate([{"$match": {"year": {'$gte': f'{filters["year"]}',
                                                                '$lte': f'{(str(int(filters["year"])+9))}'}}},
                                           {"$sample": {"size": 1}}])
    else:
        res_random = collection.aggregate([{"$match": {"fullname": {"$exists": True}}},
                                           {"$sample": {"size": 1}}])
    res = []
    try:
        async for el in res_random:
            res.append(el)
    except:
        res_random = collection.aggregate([{"$match": {"fullname": {"$exists": True}}},
                                           {"$sample": {"size": 1}}])
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
                    'genre': tag.genre,
                    'year': tag.year
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
        await collection.update_one({user: {"$exists": True}},
                                    {'$set': {'last_track': {'fullname': track, **tags}}})
    else:
        await collection.insert_one({user: {'register': str(datetime.datetime.now())}})
        await collection.update_one({user: {"$exists": True}},
                                    {'$set': {'last_track': {'fullname': track, **tags}}})


async def get_credentials():
    res = await my_music_settings.find_one({"login": {"$exists": True }})
    return res["login"]


async def get_top_genres(limit_tracks: int = 100):
    res = []
    async for el in my_music_collection.aggregate([{'$group': {'_id': '$genre', 'count': {'$sum': 1}}}]):
        if el['count'] > limit_tracks and el['_id'] is not None and 1 < len(el['_id']) < 20:
            res.append(el['_id'])
    return res


async def get_top_artists(limit_tracks: int = 100):
    res = []
    async for el in my_music_collection.aggregate([{'$group': {'_id': '$artist', 'count': {'$sum': 1}}}]):
        if el['count'] > limit_tracks and el['_id'] is not None and 1 < len(el['_id']) < 32:
            res.append(el['_id'])
    return res


async def get_artists_by_genres(genre: str):
    res = []
    async for el in my_music_collection.aggregate([{"$match": {"genre": f"{genre}"}},
                                                   {'$group': {'_id': f'$artist'}}]):
        if el['_id'] is not None and 1 < len(el['_id']) < 32:
            res.append(el['_id'])
    return res


async def get_years(limit_tracks: int = 10):
    res = []
    async for el in my_music_collection.aggregate([{'$group': {'_id': '$year', 'count': {'$sum': 1}}}]):
        if el['count'] > limit_tracks and el['_id'] is not None and len(el['_id']) == 4 \
                and el['_id'].isdigit() and 1900 < int(el['_id']) < 2100:
            decade = str(int(el['_id'])//10*10)
            if decade not in res:
                res.append(decade)
    return sorted(res)


async def update_filter(user, mode: str, genre: str = None, artist: str = None, year: str = None,
                        collection=my_music_settings):
    result = await collection.update_one({user: {"$exists": True}}, {'$set': {'filter': {'mode': mode,
                                                                                         'genre': genre,
                                                                                         'artist': artist,
                                                                                         'year': year}}})
    if result.matched_count > 0:
        return True
    else:
        return False

