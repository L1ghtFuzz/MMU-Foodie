from flask import Blueprint, render_template, request, flash, jsonify, url_for, redirect
from flask_login import login_required, current_user
from . import db
from .models import Restaurant
from flask import Flask, render_template, request, redirect, session, jsonify, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from flask_login import LoginManager
import re, os
from sqlalchemy.sql import func

views = Blueprint('views', __name__)

user_favourites = set()
user_past = set()
user_reviews = {}

@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    all_restaurants = db.session.query(Restaurant).all()
    return render_template('home.html', user=current_user, all_restaurants=all_restaurants, user_favourites=user_favourites, user_past=user_past)

@views.route('/search')
@login_required
def search():
    query = request.args.get('query', '').lower()
    results = []
    if query:
        results = [r for r in db.session.query(Restaurant).all() if query in r['name'].lower()]
    return render_template("home.html", user=current_user, results=results, query=query, all_restaurants=db.session.query(Restaurant).all()
, user_favourites=user_favourites)

@views.route('/favourite/<int:id>')
@login_required
def favourite(id):
    user_favourites.add(id)
    flash("Added to favourites!", category='success')
    return redirect(url_for('views.home'))

@views.route('/unfavourite/<int:id>')
@login_required
def unfavourite(id):
    user_favourites.discard(id)
    flash("Removed from favourites.", category='warning')
    return redirect(url_for('views.favourites_page'))

@views.route('/favourites')
@login_required
def favourites_page():
    favourites = [r for r in db.session.query(Restaurant).all() if r.id in user_favourites]
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
    past_restaurants = [r for r in db.session.query(Restaurant).all() if r.id in user_past]
    return render_template('past_restaurants.html', user=current_user, past_restaurants=past_restaurants)

# Add Restaurant 
@views.route('/restaurant/<int:restaurant_id>')
def display_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    return render_template('display.html', restaurant=restaurant)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@views.route('/form', methods=['GET', 'POST'])
@login_required
def add_restaurant():
    if not current_user.is_admin:
        flash("Access denied. Admins only.")
        return redirect(url_for('home'))

    if request.method == 'POST':
        # Gather form data
        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']
        cuisine = request.form['cuisine']
        google_maps_link = request.form['google_maps_link']
        rating = int(request.form['rating'])
        description = request.form['description']
        price = request.form['price']

        # Handle the image file upload
        if 'image' in request.files:
            image = request.files['image']
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image_path = os.path.join('static/uploads', filename)
                image.save(image_path)
                image_url = url_for('static', filename=f'uploads/{filename}')
            else:
                image_url = None  # Handle no image or invalid file type
            
        else:
            image_url = None  # Handle case when no image is uploaded

        # Create the new restaurant
        new_restaurant = Restaurant(
            name=name,
            address=address,
            phone=phone,
            cuisine=cuisine,
            google_maps_link=google_maps_link,
            rating=rating,
            description=description,
            image_url=image_url,
            price=price
        )

        db.session.add(new_restaurant)
        db.session.commit()
        flash("Restaurant Added Successfully!")
        return redirect(url_for('views.display_restaurant', restaurant_id=new_restaurant.id))

    return render_template('form.html')

# I can make a randomiser where it reaches for the one in db, using 'Restaurant.query.order_by(func.random()).first()' but needa change a lot
@views.route('/random', methods=['GET', 'POST'])
@login_required
def random_restaurant():
    selected = None
    if request.method == 'POST':
        selected = Restaurant.query.order_by(func.random()).first()
    return render_template("random.html", user=current_user, selected=selected)