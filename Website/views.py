from flask import Blueprint, render_template, request, flash, jsonify, url_for, redirect
from flask_login import login_required
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
from sqlalchemy import or_

views = Blueprint('views', __name__)
user_favourites = set()
user_past = set()

@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    print("Loading home page")
    all_restaurants = db.session.query(Restaurant).all()
    return render_template('home.html', user=current_user, all_restaurants=all_restaurants, user_favourites=user_favourites, user_past=user_past)

@views.route('/search')
@login_required
def search():
    query = request.args.get('query', '').lower()
    results = []
    if query:
        results = [r for r in db.session.query(Restaurant).all() if query in r.name.lower()]
    return render_template("home.html", user=current_user, results=results, query=query, all_restaurants=db.session.query(Restaurant).all(), user_favourites=current_user.favourites)

@views.route('/favourite/<int:id>')
@login_required
def favourite(id):
    restaurant = Restaurant.query.get_or_404(id)
    if restaurant not in current_user.favourites:
        current_user.favourites.append(restaurant)
        db.session.commit()
        flash("Added to favourites!", category='success')
    else:
        flash("Already in favourites.", category='info')
    return redirect(url_for('views.home'))

@views.route('/unfavourite/<int:id>')
@login_required
def unfavourite(id):
    restaurant = Restaurant.query.get_or_404(id)
    if restaurant in current_user.favourites:
        current_user.favourites.remove(restaurant)
        db.session.commit()
        flash("Removed from favourites.", category='warning')
    return redirect(url_for('views.favourites_page'))

@views.route('/favourites')
@login_required
def favourites_page():
    return render_template('favourites.html', user=current_user, favourites=current_user.favourites)

@views.route('/mark-past/<int:id>')
@login_required
def mark_past(id):
    restaurant = Restaurant.query.get_or_404(id)
    if restaurant not in current_user.past:
        current_user.past.append(restaurant)
        db.session.commit()
        flash("Marked as visited.", category='info')
    else:
        flash("Already marked as visited.", category='info')
    return redirect(url_for('views.home'))

@views.route('/past')
@login_required
def past_page():
    return render_template('past_restaurants.html', user=current_user, past_restaurants=user_past)

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
        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']
        cuisine = request.form['cuisine']
        google_maps_link = request.form['google_maps_link']
        rating = int(request.form['rating'])
        description = request.form['description']
        price = request.form['price']

        if 'image' in request.files:
            image = request.files['image']
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image_path = os.path.join('static/uploads', filename)
                image.save(image_path)
                image_url = url_for('static', filename=f'uploads/{filename}')
            else:
                image_url = None
        else:
            image_url = None

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

@views.route('/random', methods=['GET', 'POST'])
@login_required
def random_restaurant():
    selected = None
    # Define available cuisines and price ranges for the filter form
    available_cuisines = ['Any', 'Italian', 'Mexican', 'Japanese', 'Indian', 'Chinese', 'American', 'Cafe', 'Dessert']
    available_prices = ['Any', '$', '$$', '$$$']

    # Initialize selected_cuisine and selected_price to 'Any' as default
    # or to whatever the default value of your dropdowns should be on first load
    selected_cuisine = 'Any'
    selected_price = 'Any'

    if request.method == 'POST':
        # Get filter criteria from the form
        cuisine_filter = request.form.get('cuisine_filter')
        price_filter = request.form.get('price_filter')

        # Store the selected filters to pass back to the template
        selected_cuisine = cuisine_filter
        selected_price = price_filter

        # Start with a base query of all restaurants
        query = Restaurant.query

        # Apply cuisine filter if selected (and not 'Any')
        if cuisine_filter and cuisine_filter != 'Any':
            query = query.filter_by(cuisine=cuisine_filter)

        # Apply price filter if selected (and not 'Any')
        if price_filter and price_filter != 'Any':
            query = query.filter_by(price=price_filter)

        # Get a random restaurant from the filtered results
        selected = query.order_by(func.random()).first()

        if not selected:
            flash("No restaurants found matching your criteria. Try different filters!", category='warning')

    return render_template(
        "random.html",
        user=current_user,
        selected=selected,
        available_cuisines=available_cuisines,
        available_prices=available_prices,
        selected_cuisine=selected_cuisine, 
        selected_price=selected_price      
    )
