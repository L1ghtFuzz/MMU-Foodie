from flask import Blueprint, render_template, request, flash, jsonify, url_for, redirect
from flask_login import login_required, current_user
from .models import Restaurant
from . import db
from sqlalchemy.sql import func
import json, random

views = Blueprint('views', __name__)

hardcoded_restaurants = [
    {"id": 1, "name": "Namo Garden", "cuisine": "Thai", "location": "Cyberjaya", "description": "Lush garden setting with authentic Thai cuisine.", "image": "namo.jpg"},
    {"id": 2, "name": "Giggles and Geeks", "cuisine": "Western Fusion", "location": "Cyberjaya", "description": "Quirky cafe with geek-themed meals.", "image": "giggles.jpg"},
    {"id": 3, "name": "Woodfire Cyberjaya", "cuisine": "American", "location": "Cyberjaya", "description": "Home of juicy burgers and wood-fired delights.", "image": "kocha.jpg"},
    {"id": 4, "name": "Kocha Lala", "cuisine": "Malay", "location": "Central", "description": "A cozy spot serving authentic Malay food.", "image": "woodfire.jpg"},
    {"id": 5, "name": "10gram Cyberjaya", "cuisine": "Cafe", "location": "Cyberjaya", "description": "Modern cafe with aesthetic vibes and good coffee."},
    {"id": 6, "name": "Strawberry Fields Cafe Cyberjaya", "cuisine": "Western & Local", "location": "Cyberjaya", "description": "Casual dining with a wide variety of choices."},
    {"id": 7, "name": "Lengis Restaurant Cyberjaya", "cuisine": "Middle Eastern", "location": "Cyberjaya", "description": "Grilled meats and Middle Eastern specialties."},
    {"id": 8, "name": "After Seven Lounge", "cuisine": "Fusion", "location": "Cyberjaya", "description": "Lounge and dining experience for late evenings."}
]

user_favourites = set()
user_past = set()

@views.route('/', methods=['GET', 'POST'])
def home():
    return render_template('home.html', user=current_user, all_restaurants=hardcoded_restaurants, user_favourites=user_favourites)

@views.route('/search')
def search():
    query = request.args.get('query', '').lower()
    results = []
    if query:
        results = [r for r in hardcoded_restaurants if query in r['name'].lower()]
    return render_template("home.html", user=current_user, results=results, query=query, all_restaurants=hardcoded_restaurants, user_favourites=user_favourites)

@views.route('/favourite/<int:id>')
@login_required
def favourite(id):
    user_favourites.add(id)
    flash("Added to favourites!", category='success')
    return redirect(url_for('views.search'))

@views.route('/unfavourite/<int:id>')
@login_required
def unfavourite(id):
    user_favourites.discard(id)
    flash("Removed from favourites.", category='warning')
    return redirect(url_for('views.favourites_page'))

@views.route('/favourites')
@login_required
def favourites_page():
    favourites = [r for r in hardcoded_restaurants if r['id'] in user_favourites]
    return render_template('favourites.html', user=current_user, favourites=favourites)

@views.route('/mark-past/<int:id>')
@login_required
def mark_past(id):
    user_past.add(id)
    flash("Marked as visited.", category='info')
    return redirect(url_for('views.home'))

@views.route('/past')
@login_required
def past_page():
    past_restaurants = [r for r in hardcoded_restaurants if r['id'] in user_past]
    return render_template('past_restaurants.html', user=current_user, past_restaurants=past_restaurants)

@views.route('/random')
def random_restaurant():
    restaurant = Restaurant.query.order_by(func.random()).first()
    return render_template('rrandom.html', restaurant=restaurant)