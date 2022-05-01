#!/usr/bin/python3

import os
import subprocess
import uvicorn
import random

from fastapi import FastAPI

import schemas

proc = None

tags_metadata = [
    {
        "name": "Playback",
        "description": "Управление воспроизведением",
    },
]

app = FastAPI(
    title="Моя.Музыка Api",
    version="1.0.0",
    openapi_tags=tags_metadata,
)


@app.on_event("startup")
async def startup():
    pass


@app.on_event("shutdown")
async def shutdown():
    pass


def make_playlist():
    playlist_file = open("playlist.txt", "w+")
    num = random.randint(1,9)
    playlist_file.write(num + ".mp3")
    playlist_file.close()


@app.get("/playback", response_model=schemas.Playback, tags=["Playback"])
async def playback(operation: str):
    print(operation)
    global proc
    if operation == 'play':
        proc = subprocess.Popen(['ezstream', '-c', '/ezstream/ezstream-file_template.xml'])
    if operation == 'next':
        os.system(f'kill -SIGHUP {proc.pid} && kill -SIGUSR1 {proc.pid}')
    return {'operation': str(proc.pid)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
