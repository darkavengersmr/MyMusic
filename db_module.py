#!/usr/bin/python3

from tinytag import TinyTag

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
    res_random = collection.aggregate([{"$sample": {"size": 1}},
                                {"$match": {"fullname": { "$exists" : True }}}])
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
    if await collection.find_one({user: { "$exists" : True }}):
        await collection.replace_one({user: { "$exists" : True }}, {user: {'last_track': {'fullname': track, **tags}}}, True)
    else:
        await collection.insert_one({user: {'last_track': {'fullname': track, **tags}}})

