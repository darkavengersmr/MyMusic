#!/usr/bin/python3

import datetime
import random
import motor.motor_asyncio
from tinytag import TinyTag

from config import DBSOCKET, moods

db_client = motor.motor_asyncio.AsyncIOMotorClient(f'mongodb://{DBSOCKET}')
db = db_client.my_music
my_music_collection = db.music
my_music_settings = db.settings
my_music_history = db.history


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
        return {'mode': None, 'genre': None, 'artist': None, 'year': None, 'mood': None, 'favorite': None}


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
    elif filters['mode'] == 'favorite' and filters["favorite"] == 'Мне нравятся':
        res_random = collection.aggregate([{"$match": {user: {"like": "like"}}},
                                           {"$sample": {"size": 1}}])
    elif filters['mode'] == 'favorite' and filters["favorite"] == 'Непрослушанные':
        res_random = collection.aggregate([{"$match": {user: {"$exists": False}}},
                                           {"$sample": {"size": 1}}])
    elif filters['mode'] == 'favorite' and filters["favorite"] == 'Любимые исполнители':
        artist = await get_favorite_artist(user)
        res_random = collection.aggregate([{"$match": {"artist": artist}},
                                           {"$sample": {"size": 1}}])
    elif filters['mode'] == 'favorite' and filters["favorite"] == 'Любимые жанры':
        genre = await get_favorite_genre(user)
        res_random = collection.aggregate([{"$match": {"genre": genre}},
                                           {"$sample": {"size": 1}}])
    elif filters['mode'] == 'mood' and filters["mood"] in moods:
        mood = random.randint(0, len(moods[filters["mood"]])-1)
        res_random = collection.aggregate([{"$match": {"genre": moods[filters["mood"]][mood]}},
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
                                           {"$sample": {"size": 5}}])
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
        prev_track_doc = await collection.find_one({user: {"$exists": True}})
        track_name = prev_track_doc['last_track']['fullname']
        await collection.update_one({user: {"$exists": True}},
                                    {'$set': {'last_track': {'fullname': track, **tags},
                                              'prev_track': {'fullname': track_name, 'play': False}}})
    else:
        await collection.insert_one({user: {'register': str(datetime.datetime.now())}})
        await collection.update_one({user: {"$exists": True}},
                                    {'$set': {'last_track': {'fullname': track, **tags},
                                              "prev_track": {'fullname': track, 'play': False}}})


async def add_to_history(user, tags, collection=my_music_history):
    await collection.insert_one({user: {'date': str(datetime.datetime.now()), **tags}})


async def get_now_play(user, collection=my_music_settings):
    if await collection.find_one({user: {"$exists": True}}):
        now_play = await collection.find_one({user: {"$exists": True}})
        if now_play:
            return f"{now_play['last_track']['artist']} - {now_play['last_track']['title']}"


async def prev_track_mode(user, collection=my_music_settings):
    if await collection.find_one({user: {"$exists": True}}):
        prev_track_doc = await collection.find_one({user: {"$exists": True}})
        await collection.update_one({user: {"$exists": True}},
                                    {'$set': {'prev_track': {'play': True, 'fullname':
                                        prev_track_doc['prev_track']['fullname']}}})


async def get_prev_track(user, collection=my_music_settings):
    if await collection.find_one({user: {"$exists": True}}):
        prev_track_doc = await collection.find_one({user: {"$exists": True}})
        if 'prev_track' in prev_track_doc and 'fullname' in prev_track_doc['prev_track']:
            await collection.update_one({user: {"$exists": True}},
                                        {'$set': {'prev_track': {'play': False, 'fullname':
                                        prev_track_doc['prev_track']['fullname']}}})
            if prev_track_doc['prev_track']['play']:
                return {'fullname': prev_track_doc['prev_track']['fullname']}


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


async def get_favorite_artist(user: str):
    res = []
    async for el in my_music_collection.aggregate([{"$match": {user: {"like": "like"}}},
                                                   {'$group': {'_id': '$artist', 'count': {'$sum': 1}}}]):
        if el['_id'] is not None:
            res.append(el['_id'])
    if len(res) > 0:
        return res[random.randint(0, len(res))-1]


async def get_favorite_genre(user: str):
    res = []
    async for el in my_music_collection.aggregate([{"$match": {user: {"like": "like"}}},
                                                   {'$group': {'_id': '$genre', 'count': {'$sum': 1}}}]):
        if el['_id'] is not None:
            res.append(el['_id'])
    if len(res) > 0:
        return res[random.randint(0, len(res))-1]


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


async def update_filter(user, mode: str, genre: str = None, artist: str = None, year: str = None, mood: str = None,
                        favorite: str = None, collection=my_music_settings):
    result = await collection.update_one({user: {"$exists": True}}, {'$set': {'filter': {'mode': mode,
                                                                                         'genre': genre,
                                                                                         'artist': artist,
                                                                                         'year': year,
                                                                                         'mood': mood,
                                                                                         'favorite': favorite}}})
    if result.matched_count > 0:
        return True
    else:
        return False


async def update_user_active(user, collection=my_music_settings):
    if not await collection.find_one({user: {"$exists": True}}):
        await collection.insert_one({user: {'register': str(datetime.datetime.now())}})
    await collection.update_one({user: {"$exists": True}}, {'$set': {'active': 5}})


async def discrement_user_active(user, collection=my_music_settings):
    if not await collection.find_one({user: {"$exists": True}}):
        await update_user_active(user)
    value = await collection.find_one({user: {"$exists": True}})
    discremented = value['active'] - 1
    await collection.update_one({user: {"$exists": True}}, {'$set': {'active': discremented}})


async def user_is_active(user, collection=my_music_settings):
    if not await collection.find_one({user: {"$exists": True}}):
        await update_user_active(user)
    value = await collection.find_one({user: {"$exists": True}})
    if 'active' in value and value['active'] > 0:
        return True
    else:
        return False


async def set_like_dislike(user, feedback, music_collection=my_music_collection, setting_collection=my_music_settings):
    user_profile = await setting_collection.find_one({user: {"$exists": True}})
    if user_profile and 'last_track' in user_profile:
        current_track = user_profile['last_track']['fullname']
    doc_track = await music_collection.find_one({'fullname': current_track})
    like_now = None
    if doc_track and user in doc_track and 'like' in doc_track[user]:
        like_now = doc_track[user]['like']
    if feedback == 'like' and like_now != 'like':
        await music_collection.update_one({'fullname': current_track}, {'$set': {user: {'like': 'like'}}})
    elif feedback == 'like' and like_now == 'like':
        await music_collection.update_one({'fullname': current_track}, {'$set': {user: {'like': 'neutral'}}})
    elif feedback == 'dislike' and like_now != 'dislike':
        await music_collection.update_one({'fullname': current_track}, {'$set': {user: {'like': 'dislike'}}})
    elif feedback == 'dislike' and like_now == 'dislike':
        await music_collection.update_one({'fullname': current_track}, {'$set': {user: {'like': 'neutral'}}})


async def get_like_dislike(user, music_collection=my_music_collection, setting_collection=my_music_settings):
    like_now = 'neutral'
    user_profile = await setting_collection.find_one({user: {"$exists": True}})
    if user_profile and 'last_track' in user_profile:
        current_track = user_profile['last_track']['fullname']
    doc_track = await music_collection.find_one({'fullname': current_track})
    if doc_track and user in doc_track and 'like' in doc_track[user]:
        like_now = doc_track[user]['like']
    return like_now


async def set_options(user, options, collection=my_music_settings):
    result = await collection.update_one({user: {"$exists": True}}, {'$set': {'options': options}})
    if result.matched_count > 0:
        return True
    else:
        return False


async def get_options(user, collection=my_music_settings):
    settings = await collection.find_one({user: {"$exists": True}})
    if settings and 'options' in settings:
        return settings['options']
    else:
        return {'radio_effect': True, 'normalize': True, 'external_player': False, 'quality': "2"}


async def create_db_user(user, collection=my_music_settings):
    logins = await collection.find_one({'login': {"$exists": True}})
    result = await collection.update_one({'login': {"$exists": True}},
                                         {'$set': {'login': {**logins['login'], user['username']: user['password']}}})
    if result.matched_count > 0:
        return True
    else:
        return False



