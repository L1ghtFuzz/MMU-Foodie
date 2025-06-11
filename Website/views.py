# Website/views.py
from flask import Blueprint, render_template, request, flash, jsonify, url_for, redirect
from flask_login import login_required, current_user
from . import db
from .models import Restaurant, Collection, Note
from flask import Flask, render_template, request, redirect, session, jsonify, flash, url_for 
from flask_sqlalchemy import SQLAlchemy 
from datetime import datetime 
from werkzeug.security import generate_password_hash, check_password_hash 
from werkzeug.utils import secure_filename
from flask_login import UserMixin, login_user, login_required, logout_user, current_user 
from flask_migrate import Migrate 
from flask_login import LoginManager 
import re, os, random
from sqlalchemy.sql import func
from sqlalchemy import or_ 

views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    print("Loading home page")
    all_restaurants = db.session.query(Restaurant).all()
    # --- FIX: Pass current_user relationships directly ---
    return render_template('home.html', user=current_user, all_restaurants=all_restaurants, user_favourites=current_user.favourites, user_past=current_user.past)
    # -----------------------------------------------------

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
    # --- FIX: Pass current_user.past directly ---
    return render_template('past_restaurants.html', user=current_user, past_restaurants=current_user.past)
    # -------------------------------------------

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
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']
        cuisine = request.form['cuisine']
        # REMOVED: The line for Maps_link = request.form['Maps_link']
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
            # REMOVED: Maps_link=Maps_link, from here
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
    available_cuisines = ['Any', 'Italian', 'Mexican', 'Japanese', 'Indian', 'Chinese', 'American', 'Cafe', 'Dessert']
    available_prices = ['Any', '$', '$$', '$$$']

    selected_cuisine = 'Any'
    selected_price = 'Any'

    if request.method == 'POST':
        cuisine_filter = request.form.get('cuisine_filter')
        price_filter = request.form.get('price_filter')

        selected_cuisine = cuisine_filter
        selected_price = price_filter

        query = Restaurant.query

        if cuisine_filter and cuisine_filter != 'Any':
            query = query.filter_by(cuisine=cuisine_filter)

        if price_filter and price_filter != 'Any':
            query = query.filter_by(price=price_filter)

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

@views.route('/notes', methods=['GET', 'POST'])
@login_required
def session_notes():
    if request.method == 'POST':
        note_content = request.form.get('note')
        if note_content:
            new_note_db = Note(data=note_content, user_id=current_user.id)
            db.session.add(new_note_db) 
            db.session.commit() 
            flash("Note added to database!", category='success')
        else:
            flash("Note cannot be empty!", category='error')


    user_notes = Note.query.filter_by(user_id=current_user.id).all()

    return render_template('notes.html', user=current_user, notes=user_notes)

@views.route('/past-restaurants')
@login_required
def past_restaurants():
    # current_user.past automatically gives you the list of associated Restaurant objects
    return render_template('past.html', user=current_user) 

@views.route('/collections', methods=['GET', 'POST'])
@login_required
def collections():
    if request.method == 'POST':
        collection_name = request.form.get('collection_name')
        if collection_name:
            # Check if a collection with the same name already exists for the user
            existing_collection = Collection.query.filter_by(name=collection_name, user_id=current_user.id).first()
            if existing_collection:
                flash(f"Collection '{collection_name}' already exists!", category='error')
            else:
                new_collection = Collection(name=collection_name, user_id=current_user.id)
                db.session.add(new_collection)
                db.session.commit()
                flash(f"Collection '{collection_name}' created successfully!", category='success')
        else:
            flash("Collection name cannot be empty!", category='error')
        return redirect(url_for('views.collections')) # Redirect to prevent form resubmission

    # For GET requests, render the page with the user's collections
    return render_template('collections.html', user=current_user)


# NEW: Route to view the details of a single collection
@views.route('/collections/<int:collection_id>')
@login_required
def collection_detail(collection_id):
    collection = Collection.query.get_or_404(collection_id)
    # Ensure the collection belongs to the current user
    if collection.user_id != current_user.id:
        flash("You do not have permission to view this collection.", category='error')
        return redirect(url_for('views.collections'))
    
    return render_template('collection_detail.html', user=current_user, collection=collection)

@views.route('/add-to-collection', methods=['POST'])
@login_required
def add_restaurant_to_collections():
    restaurant_id = request.form.get('restaurant_id')
    collection_ids = request.form.getlist('collection_ids') # getlist is used for multiple checkboxes with the same name

    if not restaurant_id:
        flash('No restaurant selected.', category='error')
        return redirect(request.referrer or url_for('views.random_restaurant')) # Go back to the page they came from

    restaurant = Restaurant.query.get(restaurant_id)
    if not restaurant:
        flash('Restaurant not found.', category='error')
        return redirect(request.referrer or url_for('views.random_restaurant'))

    if not collection_ids:
        flash('Please select at least one collection.', category='error')
        return redirect(request.referrer or url_for('views.random_restaurant'))

    collections_added_to = []
    for coll_id in collection_ids:
        collection = Collection.query.get(coll_id)
        if collection and collection.user_id == current_user.id:
            if restaurant not in collection.restaurants: # Check if restaurant is already in collection
                collection.restaurants.append(restaurant)
                collections_added_to.append(collection.name)
            else:
                flash(f"'{restaurant.name}' is already in '{collection.name}'.", category='info')
        else:
            flash(f"Collection with ID {coll_id} not found or you don't own it.", category='error')

    if collections_added_to:
        db.session.commit()
        flash(f"'{restaurant.name}' added to: {', '.join(collections_added_to)}!", category='success')
    elif not collections_added_to and collection_ids: 
        flash(f"'{restaurant.name}' was already in the selected collections.", category='info')
    
    return redirect(request.referrer or url_for('views.random_restaurant')) 

