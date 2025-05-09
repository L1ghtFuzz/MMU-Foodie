from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func

# Association table for many-to-many relationship
favourites = db.Table(
    'favourites',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('restaurant_id', db.Integer, db.ForeignKey('restaurant.id'))
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    favourites = db.relationship('Restaurant', secondary='favourites', backref='liked_by')
    is_admin = db.Column(db.Boolean, default=False)

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    cuisine = db.Column(db.String(100))
    location = db.Column(db.String(150))
    description = db.Column(db.String(255))