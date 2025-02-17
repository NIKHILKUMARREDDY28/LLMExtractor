from pydantic_settings import BaseSettings

from dotenv import find_dotenv

class Settings(BaseSettings):
    OPENAI_API_KEY: str



env_file_path = find_dotenv(".env")

settings = Settings(_env_file=env_file_path, _env_file_encoding="utf-8")