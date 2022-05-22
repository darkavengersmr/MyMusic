#!/usr/bin/python3

import os
import subprocess
from datetime import datetime, timedelta

import asyncio
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from passlib.context import CryptContext

from starlette.requests import Request
from starlette.responses import StreamingResponse
from starlette.background import BackgroundTask

from sse_starlette.sse import EventSourceResponse

import httpx

import schemas

from config import SECRET_KEY, EXCEPTION_PER_SEC_LIMIT, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, MUSIC_STREAM_SOCKET, \
    MY_INVITE

from db_module import get_credentials, get_top_genres, get_top_artists, get_artists_by_genres, get_years, \
    update_filter, update_user_active, set_like_dislike, get_like_dislike, prev_track_mode, get_filters, get_now_play, \
    set_options, get_options, create_db_user

client = httpx.AsyncClient(base_url=MUSIC_STREAM_SOCKET)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth")

proc_pid = {}
users_now_play = {}

tags_metadata = [
    {
        "name": "Register",
        "description": "Регистрация",
    },
    {
        "name": "Auth",
        "description": "Авторизация",
    },
    {
        "name": "Playback",
        "description": "Управление воспроизведением (operation: play, stop, next, prev)",
    },
    {
        "name": "Filter",
        "description": "Управление предпочтениями (modes: genres, artists_by_genre)",
    },
    {
        "name": "Play Now",
        "description": "Что играет сейчас (Server side events)",
    },
    {
        "name": "Feedback",
        "description": "Лайки, дислайки, другая обратная связь",
    },
    {
        "name": "Options",
        "description": "Настройки клиентского приложения",
    },
]

app = FastAPI(
    title="Моя.Музыка Api",
    version="1.0.0",
    openapi_tags=tags_metadata,
)

command_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Command not valid",
    )


@app.on_event("startup")
async def startup():
    pass


@app.on_event("shutdown")
async def shutdown():
    pass


async def authenticate_user(username: str, password: str):
    credentials = await get_credentials()
    if username in credentials and credentials[username] == password:
        return True
    else:
        return False


def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    credentials = await get_credentials()
    if token_data.username in credentials:
        return {'username': token_data.username}
    else:
        raise credentials_exception


@app.get("/")
async def redirect_login():
    return RedirectResponse(url=f"/index.html", status_code=303)


@app.post("/register", response_model=schemas.UserRegisterResult, tags=["Register"])
async def create_user(user: schemas.UserRegister):
    db_users = await get_credentials()
    if user.username in db_users:
        await asyncio.sleep(EXCEPTION_PER_SEC_LIMIT)
        raise HTTPException(status_code=400, detail="User with this email already registered")
    if user.invite != MY_INVITE:
        await asyncio.sleep(EXCEPTION_PER_SEC_LIMIT)
        raise HTTPException(status_code=400, detail="Invite is broken")
    if await create_db_user(dict(user)):
        return {'result': f'New user {user.username} registered'}
    else:
        return {'result': f'Error registration'}


@app.post("/auth", response_model=schemas.Token , tags=["Auth"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        await asyncio.sleep(EXCEPTION_PER_SEC_LIMIT)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/playback", response_model=schemas.Playback, tags=["Playback"])
async def playback(operation: str, current_user: schemas.User = Depends(get_current_user)):
    user = current_user['username']
    if operation == 'play':
        if user not in proc_pid:
            template_out = open(f"ezstream_{user}.xml", "w")
            with open("ezstream_template.xml", "r") as template_in:
                for line in template_in:
                    template_out.write(line.replace('%USERNAME%', user))
            template_out.close()
            os.system(f'cp playlist.py playlist_{user}.py')
            proc_pid[user] = subprocess.Popen(['ezstream', '-c', f'/ezstream/ezstream_{user}.xml']).pid
    elif operation == 'stop':
        if user in proc_pid:
            os.system(f'rm ezstream_{user}.xml')
            os.system(f'rm playlist_{user}.py')
            subprocess.Popen(['kill', '-9', str(proc_pid[user])])
            proc_pid.pop(user)
    elif operation == 'next' or operation == 'prev':
        if user in proc_pid:
            if operation == 'prev':
                await prev_track_mode(user)
            subprocess.Popen(['kill', '-SIGHUP', str(proc_pid[user])])
            subprocess.Popen(['kill', '-SIGUSR1', str(proc_pid[user])])
            return {f'operation': 'prev/next ok', 'username': user}
        else:
            return {f'operation': 'status: stop', 'username': user}
    elif operation == 'status':
        filters = await get_filters(user)
        if user in proc_pid:
            now_play = await get_now_play(user)
            return {f'operation': 'status: play', 'username': user, 'now_play': now_play, **filters, }
        else:
            return {f'operation': 'status: stop', 'username': user, 'now_play': None, **filters}
    else:
        raise command_exception
    return {f'operation': f'{operation} ok', 'username': user}


@app.get("/filter", response_model=schemas.MyFilterOut, tags=["Filter"])
async def get_filter(mode: str, genre: str = None, limit_tracks: int = 100,
                     current_user: schemas.User = Depends(get_current_user)):
    if mode == 'genres':
        return {'result': await get_top_genres(limit_tracks=limit_tracks)}
    elif mode == 'artists':
        return {'result': await get_top_artists(limit_tracks=limit_tracks)}
    elif mode == 'artists_by_genre' and genre is not None:
        return {'result': await get_artists_by_genres(genre)}
    if mode == 'years':
        return {'result': await get_years(limit_tracks=limit_tracks)}
    else:
        raise command_exception


@app.post("/filter", response_model=schemas.MyFilterSet, tags=["Filter"])
async def set_filter(mode: str, genre: str = None, artist: str = None, year: str = None, mood: str = None,
                     favorite: str = None, current_user: schemas.User = Depends(get_current_user)):
    user = current_user['username']
    modes = ['genre', 'artist', 'year', 'mood', 'favorite']
    if mode in modes and await update_filter(user, mode=mode, genre=genre, artist=artist, year=year, mood=mood,
                                             favorite=favorite):
        return {'result': 'filter ok'}
    else:
        raise command_exception


@app.post("/now_play", response_model=schemas.PlayNowSet, tags=["Play Now"])
async def set_now_play(now_play: str, current_user: schemas.User = Depends(get_current_user)):
    user = current_user['username']
    like = await get_like_dislike(user)
    users_now_play[user] = f'{now_play} |{like}'
    return {'result': f'update play now: {now_play}'}


@app.delete("/now_play", response_model=schemas.PlayNowSet, tags=["Play Now"])
async def set_now_play(current_user: schemas.User = Depends(get_current_user)):
    user = current_user['username']
    if user in users_now_play:
        users_now_play.pop(user)
        await update_user_active(user)
        return {'result': f'deletes play now'}
    else:
        return {'result': f'nothing to delete'}


# SSE - Server side events - пушим на пользователя метаинформации из трека, который запустился
@app.get('/now_play', tags=["Play Now"])
async def message_stream(request: Request, user: str):
    def new_messages():
        if user in users_now_play:
            return users_now_play[user]
        else:
            return None

    async def event_generator():
        while True:
            # If client closes connection, stop sending events
            if await request.is_disconnected():
                break

            # Checks for new messages and return them to client if any
            message = new_messages()
            if message:
                print("попытка отправки...")
                yield message

            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


@app.post("/feedback", response_model=schemas.PlayNowSet, tags=["Feedback"])
async def set_feedback(feedback: str, current_user: schemas.User = Depends(get_current_user)):
    user = current_user['username']
    if feedback == 'like' or feedback == 'dislike':
        await set_like_dislike(user, feedback)
    else:
        raise command_exception
    return {'result': f'feedback ok'}


@app.get("/options", response_model=schemas.Options, tags=["Options"])
async def read_options(current_user: schemas.User = Depends(get_current_user)):
    user = current_user['username']
    return await get_options(user)


@app.put("/options", response_model=schemas.Options, tags=["Options"])
async def update_options(options: schemas.Options, current_user: schemas.User = Depends(get_current_user)):
    user = current_user['username']
    if await set_options(user, dict(options)):
        return {'result': 'options ok'}
    else:
        raise command_exception


async def _reverse_proxy(request: Request):
    url = httpx.URL(path=request.url.path,
                    query=request.url.query.encode("utf-8"))
    rp_req = client.build_request(request.method, url,
                                  headers=request.headers.raw,
                                  content=await request.body())
    rp_resp = await client.send(rp_req, stream=True)
    return StreamingResponse(
        rp_resp.aiter_raw(),
        status_code=rp_resp.status_code,
        headers=rp_resp.headers,
        background=BackgroundTask(rp_resp.aclose),
    )


app.add_route("/stream_{name}.ogg",
              _reverse_proxy, ["GET", "POST"])


app.mount("/", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
