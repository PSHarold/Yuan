import flask

from app.Models.facepp import API
from config import Config

config = Config()
face_api = API(key='1d1ae053ef9d53ce1cd319fbfd25d069', secret='L9ONeuqKNOCvgdrMUiF9k5VYkTegv30-')


def create_app():
    app = flask.Flask(__name__)
    config.init_app(app)
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    return app
