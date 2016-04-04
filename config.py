import mongoengine


class Config:
    @staticmethod
    def init_app(app):
        app.config['SECRET_KEY'] = 'mysecretsecretkey'

        mongoengine.connect('face_database')
        return app