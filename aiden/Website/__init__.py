from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate  # ✅ NEW
from os import path
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()  # ✅ NEW
DB_NAME = "database.db"


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'hjshjhdjah kjshkjdhjs'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'

    db.init_app(app)
    migrate.init_app(app, db)  # ✅ NEW

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User, Note  # Make sure to import Restaurant too if used elsewhere

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app


def create_database(app):
    if not path.exists('website/' + DB_NAME):
        db.create_all(app=app)
        print('Created Database!')

def seed_restaurants():

    from .models import Restaurant

    if not Restaurant.query.first():
        sample_data = [
            Restaurant(name="Woodfire Cyberjaya", cuisine="Western", location="Downtown"),
            Restaurant(name="Namo Garden", cuisine="Italian", location="West End"),
            Restaurant(name="Kocha Lala", cuisine="Mexican", location="East Side")
]
        db.session.bulk_save_objects(sample_data)
        db.session.commit()

    if not Restaurant.query.filter_by(name="Kocha Lala").first():
        kocha = Restaurant(
            name="Kocha Lala",
            cuisine="Malay",
            location="Central",
            description="A cozy spot serving authentic Malay food."
        )
        db.session.add(kocha)
        db.session.commit()
        
        kocha = Restaurant(
    name="Kocha Lala",
    cuisine="Malay",
    location="Central",
    description="A cozy spot serving authentic Malay food.",
    image_url="/static/images/kocha_lala.jpg"  # or use a full URL
)