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

import httpx

import schemas

from config import SECRET_KEY, EXCEPTION_PER_SEC_LIMIT, \
    ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, MUSIC_STREAM_SOCKET

from db_module import get_credentials

client = httpx.AsyncClient(base_url=MUSIC_STREAM_SOCKET)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth")

proc_pid = {}

tags_metadata = [
    {
        "name": "Auth",
        "description": "Авторизация",
    },
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
    command_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Command not valid",
    )
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
    elif operation == 'next':
        if user in proc_pid:
            subprocess.Popen(['kill', '-SIGHUP', str(proc_pid[user])])
            subprocess.Popen(['kill', '-SIGUSR1', str(proc_pid[user])])
            return {f'operation': 'next ok', 'username': user}
        else:
            return {f'operation': 'status: stop', 'username': user}
    elif operation == 'status':
        if user in proc_pid:
            return {f'operation': 'status: play', 'username': user}
        else:
            return {f'operation': 'status: stop', 'username': user}
    else:
        raise command_exception
    return {f'operation': f'{operation} ok', 'username': user}


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
