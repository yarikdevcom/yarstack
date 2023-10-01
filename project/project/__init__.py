from flask import Flask
from asgiref.wsgi import WsgiToAsgi
from pydantic_settings import BaseSettings, SettingsConfigDict

app = Flask(__name__)
asgi_app = WsgiToAsgi(app)

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    host: str
    port: int
    env: str
    branch: str

settings = AppSettings()

@app.route("/")
def index():
    return f"Hello World: {settings.env} -> {settings.branch}"
