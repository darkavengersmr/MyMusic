#!/usr/bin/python3

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
    return await collection.find_one({})


async def add_to_db(collection, playlist):
    documents = []
    with open(playlist, "r") as my_playlist:
        for file in my_playlist:
            documents.append({'fullname': file})

    await do_insert_many(collection, documents)


async def update_now_play(collection, user, track):
    await collection.insert_one({'user: track'})
