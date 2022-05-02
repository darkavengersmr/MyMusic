#!/usr/bin/python3

import subprocess
from datetime import datetime, timedelta

import asyncio
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
#from fastapi.staticfiles import StaticFiles
#from fastapi.responses import RedirectResponse, FileResponse
from jose import JWTError, jwt
from passlib.context import CryptContext

import schemas

from config import USER, PASSWORD, SECRET_KEY, EXCEPTION_PER_SEC_LIMIT, \
    ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth")

proc = None

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
    if username == USER and password == PASSWORD:
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
    #user = await get_user(username=token_data.username)
    if token_data.username == USER:
        return {'username': USER}
    else:
        raise credentials_exception


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
    global proc
    if operation == 'play':
        proc = subprocess.Popen(['ezstream', '-c', '/ezstream/ezstream-file_template.xml'])
    elif operation == 'stop':
        proc = subprocess.Popen(['kill', '-9', str(proc.pid)])
    elif operation == 'next':
        subprocess.Popen(['kill', '-SIGHUP', str(proc.pid)])
        subprocess.Popen(['kill', '-SIGUSR1', str(proc.pid)])
    else:
        raise command_exception
    return {f'operation': f'{operation} ok'}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
