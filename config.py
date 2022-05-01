from starlette.config import Config
import schemas

config = Config(schemas.Settings.Config.env_file)

USER = config('USER')
PASSWORD = config('PASSWORD')
SECRET_KEY = config('SECRET_KEY')
EXCEPTION_PER_SEC_LIMIT = config('EXCEPTION_PER_SEC_LIMIT', cast=int)
ALGORITHM = config('ALGORITHM')
ACCESS_TOKEN_EXPIRE_MINUTES = config('ACCESS_TOKEN_EXPIRE_MINUTES', cast=int)

