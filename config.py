from starlette.config import Config
import schemas

config = Config(schemas.Settings.Config.env_file)

SECRET_KEY = config('SECRET_KEY')
EXCEPTION_PER_SEC_LIMIT = config('EXCEPTION_PER_SEC_LIMIT', cast=int)
ALGORITHM = config('ALGORITHM')
ACCESS_TOKEN_EXPIRE_MINUTES = config('ACCESS_TOKEN_EXPIRE_MINUTES', cast=int)
DBSOCKET = config('DBSOCKET')
MUSIC_STREAM_SOCKET = config('MUSIC_STREAM_SOCKET')

moods = {
        "Энергичное": ['Heavy Metal', 'Rockabilly Metal', 'Power Metal', 'Pop-Rock', 'Metal', 'Rock', 'Thrash Metal', 'Electronic', 'Rock & Roll', 'Glam Metal', 'Pop', 'Punk Rock', 'Hard Rock'],
        "Спокойное": ['Ballad', 'Reggae', 'Retro', 'Classical', 'Blues', 'Jazz', 'Vocal', 'Oldies'],
        "Радостное": ['Ballad', 'Reggae', 'Pop-Rock', 'Rock', 'Jazz', 'Classic Soft Rock', 'Rock & Roll', 'Glam Metal', 'Rock, Humour', 'Country', 'Pop', 'Bachata'],
        "Грустное": ['Ballad', 'Classical', 'Blues'],
        "Расслабленное": ['Ballad', 'Reggae', 'Retro', 'Classical', 'Jazz', 'Acid Jazz', 'Country', 'Pop'],
        "Мрачное": ['Heavy Metal', 'Metal', 'Blues', 'Thrash Metal', 'Hard Rock'],
        "Мечтательное": ['Ballad', 'Reggae', 'Pop-Rock', 'Retro', 'Classical', 'Blues', 'Soundtrack', 'Jazz', 'Oldies', 'Pop'],
        "Сентиментальное": ['Ballad', 'Retro', 'Country'],
        "Эпичное": ['Power Metal', 'Celtic'],
        "Рабочее": ['Pop-Rock', 'Retro', 'Classical', 'Jazz', 'Electronic', 'Instrumental'],
        "Бодрое": ['Power Metal', 'Rock', 'Rock & Roll', 'Glam Metal', 'Pop'],
        "Мистическое": ['Celtic', 'New Age'],
        "Романтическое": ['Ballad', 'Retro', 'Classical', 'Jazz',  'Bachata', 'Instrumental'],
}