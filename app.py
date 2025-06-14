from flask import Flask, render_template, request, redirect, flash, url_for, current_app
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, time
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from flask_login import LoginManager
from sqlalchemy.sql import func
from math import radians, cos, sin, sqrt, atan2
import re, os, uuid, random
import pytz

malaysia_tz = pytz.timezone('Asia/Kuala_Lumpur')

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(app.root_path, 'instance', 'database.db')}"
app.secret_key = 'odiajfiouwhaldiu213978yASd'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Data Classes
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    favourites = db.relationship('Restaurant', secondary='favourites', backref='liked_by')
    # ADDED: Relationship for past visited restaurants
    past = db.relationship('Restaurant', secondary='past', backref='visited_by')
    is_admin = db.Column(db.Boolean, default=False)
    collections = db.relationship('Collection', backref='owner', lazy=True)

favourites = db.Table(
    'favourites',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('restaurant_id', db.Integer, db.ForeignKey('restaurant.id'))
)

past = db.Table(
    'past',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('restaurant_id', db.Integer, db.ForeignKey('restaurant.id'))
)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10000))
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    cuisine = db.Column(db.String(100))
    price = db.Column(db.String(4))
    Maps_link = db.Column(db.String(300))
    description = db.Column(db.Text)
    image_url = db.Column(db.String(300))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    is_saved = db.Column(db.Boolean, default=False)
    reviews = db.relationship('Review', backref='restaurant', lazy=True)
    images = db.relationship('RestaurantImage', backref='restaurant', cascade='all, delete-orphan')
    operating_hours = db.relationship('OperatingHour', backref='restaurant', lazy=True, cascade='all, delete-orphan')
    is_24_hours = db.Column(db.Boolean, default=False)

    @property
    def average_rating(self):
        reviews = self.reviews
        if reviews:
            return sum(review.rating for review in reviews) / len(reviews)
        return None

    def get_status(self):
        now = datetime.now()
        current_day = now.strftime('%A')
        current_time = now.time()

        if self.is_24_hours:
            return "Open now", "24 Hours"

        today_hours = None
        for oh in self.operating_hours:
            if oh.day_of_week == current_day:
                today_hours = oh
                break

        if not today_hours or today_hours.open_time == 'Closed':
            days_of_week_ordered = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            current_day_index = days_of_week_ordered.index(current_day)

            for i in range(1, 8):
                next_day_index = (current_day_index + i) % 7
                next_day_name = days_of_week_ordered[next_day_index]
                next_day_hours = next((oh for oh in self.operating_hours if oh.day_of_week == next_day_name), None)

                if next_day_hours and next_day_hours.open_time != 'Closed':
                    next_open_time_str = next_day_hours.open_time
                    # Convert to time object
                    next_open_time = datetime.strptime(next_open_time_str, '%H:%M').time()
                    return "Closed now", f"Opens {next_day_name} at {next_open_time.strftime('%I:%M %p')}"
            return "Closed now", "No upcoming opening hours."

        open_time_obj = datetime.strptime(today_hours.open_time, '%H:%M').time()
        close_time_obj = datetime.strptime(today_hours.close_time, '%H:%M').time()

        if open_time_obj <= current_time <= close_time_obj:
            return "Open now", f"Closes at {close_time_obj.strftime('%I:%M %p')}"
        elif current_time < open_time_obj:
            return "Closed now", f"Opens at {open_time_obj.strftime('%I:%M %p')}"
        else:
            days_of_week_ordered = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            current_day_index = days_of_week_ordered.index(current_day)

            for i in range(1, 8):
                next_day_index = (current_day_index + i) % 7
                next_day_name = days_of_week_ordered[next_day_index]
                next_day_hours = next((oh for oh in self.operating_hours if oh.day_of_week == next_day_name), None)

                if next_day_hours and next_day_hours.open_time != 'Closed':
                    next_open_time_str = next_day_hours.open_time
                    next_open_time = datetime.strptime(next_open_time_str, '%H:%M').time()
                    return "Closed now", f"Opens {next_day_name} at {next_open_time.strftime('%I:%M %p')}"
            return "Closed now", "No upcoming opening hours."

    def __repr__(self):
        return f'<Restaurant {self.name}>'


class OperatingHour(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    day_of_week = db.Column(db.String(10), nullable=False)
    open_time = db.Column(db.String(5))
    close_time = db.Column(db.String(5))

    __table_args__ = (db.UniqueConstraint('restaurant_id', 'day_of_week', name='uq_restaurant_day'),)

    def __repr__(self):
        return f'<OperatingHour {self.day_of_week}: {self.open_time}-{self.close_time} for R:{self.restaurant_id}>'

class RestaurantImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(300), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100))
    def __repr__(self):
        return f'<Review by {self.author or "Anonymous"} for Restaurant {self.restaurant_id}>'

collection_restaurants = db.Table(
    'collection_restaurants',
    db.Column('collection_id', db.Integer, db.ForeignKey('collection.id')),
    db.Column('restaurant_id', db.Integer, db.ForeignKey('restaurant.id'))
)

class Collection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id')) # Link to the User who owns the collection
    restaurants = db.relationship('Restaurant', secondary=collection_restaurants, backref='collections')


@app.cli.command("init-db")
def init_db_command():
    """Clear existing data and create new tables."""
    with app.app_context():
        db.create_all()
    print("Database initialized (tables created).")

# Routes
@app.route("/base")
def base():
    return render_template('base.html')

@app.route('/')
@app.route('/index')
def index():
    query = db.session.query(Restaurant, func.avg(Review.rating).label('avg_rating')) \
                      .outerjoin(Review).group_by(Restaurant.id)
    search_term = request.args.get('search')
    if search_term:
        query = query.filter(Restaurant.name.ilike(f'%{search_term}%'))

    min_rating = request.args.get('rating', type=int)
    price = request.args.get('price')
    category_param = request.args.get('category')
    open_now = request.args.get('open_now') # Get the 'open_now' parameter

    user_lat = request.args.get('user_lat', type=float)
    user_lon = request.args.get('user_lon', type=float)
    distance_limit = request.args.get('distance')

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c


    if min_rating:
        query = query.having(func.avg(Review.rating) >= min_rating)
    if price:
        query = query.filter(Restaurant.price == price)
    if category_param:
        categories = category_param.split(',')
        query = query.filter(Restaurant.cuisine.in_(categories))

    all_restaurants = query.all() # Get all restaurants first to filter by open_now
    restaurants = []

    for restaurant, avg_rating in all_restaurants:
        restaurant.avg_rating = round(avg_rating or 0, 1)

        # Filter by "Open Now"
        if open_now == 'true':
            status, _ = restaurant.get_status()
            if status != "Open now":
                continue # Skip if not open now

        if user_lat and user_lon and distance_limit and distance_limit != 'bird':
            if restaurant.latitude and restaurant.longitude:
                distance_km = haversine(user_lat, user_lon, restaurant.latitude, restaurant.longitude)
                if distance_km > float(distance_limit):
                    continue

        restaurants.append(restaurant)

    random.shuffle(restaurants)

    return render_template('index.html', restaurants=restaurants)

@app.route("/admin-dashboard", methods=["GET", "POST"])
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Access denied. Admins only.", category='error')
        return redirect(url_for('index'))

    restaurants = Restaurant.query.all()
    return render_template("admin-dashboard.html", user=current_user, restaurants=restaurants)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user and check_password_hash(user.password, password):
            login_user(user, remember=True)
            return redirect(url_for('admin_dashboard') if user.is_admin else url_for('index'))
        else:
            flash('Invalid credentials', category='error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        first_name = request.form.get('firstName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        password_pattern = r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}$'

        user_by_email = User.query.filter_by(email=email).first()
        user_by_username = User.query.filter_by(username=username).first()

        if user_by_email:
            flash('Email already exists.', category='error')
        elif user_by_username:
            flash('Username already exists.', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        elif len(first_name) < 2:
            flash('First name must be greater than 1 character.', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif not re.match(password_pattern, password1):
            flash('Password must include at least 8 characters, a number, an uppercase and a lowercase letter.', category='error')
        else:
            new_user = User(
                email=email,
                username=username,
                first_name=first_name,
                password=generate_password_hash(password1, method='pbkdf2:sha256')
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('Account created!', category='success')
            return redirect(url_for('index')) # Changed from dashboard to index
    return render_template("sign-up.html", user=current_user)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Store original values to determine what changed
        original_username = current_user.username
        original_email = current_user.email
        original_first_name = current_user.first_name

        new_username = request.form.get('username')
        new_email = request.form.get('email')
        new_first_name = request.form.get('firstName')

        updated_fields = []

        # Check for existing username (if changed)
        if new_username and new_username != original_username:
            user_by_username = User.query.filter_by(username=new_username).first()
            if user_by_username and user_by_username.id != current_user.id: # Ensure it's not the current user's own existing username
                flash('Username already exists. Please choose a different one.', category='error')
                return redirect(url_for('profile'))
            current_user.username = new_username
            updated_fields.append('username')

        # Check for existing email (if changed)
        if new_email and new_email != original_email:
            user_by_email = User.query.filter_by(email=new_email).first()
            if user_by_email and user_by_email.id != current_user.id: # Ensure it's not the current user's own existing email
                flash('Email already exists. Please use a different email address.', category='error')
                return redirect(url_for('profile'))
            current_user.email = new_email
            updated_fields.append('email')

        # Update first name (no uniqueness check needed)
        if new_first_name != original_first_name:
            current_user.first_name = new_first_name
            updated_fields.append('first name')

        if updated_fields:
            db.session.commit()
            if len(updated_fields) == 1:
                flash(f'{updated_fields[0].capitalize()} updated successfully!', category='success')
            else:
                flash(f'{", ".join(updated_fields).capitalize()} updated successfully!', category='success')
        else:
            flash('No changes detected.', category='info')

        return redirect(url_for('profile'))

    return render_template('profile.html', user=current_user)

# Restaurant Things
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

@app.route('/restaurant/<int:restaurant_id>')
def display_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    status, status_detail = restaurant.get_status()

    # Prepare operating hours for display
    operating_hours_display = {oh.day_of_week: {'open_time': oh.open_time, 'close_time': oh.close_time} for oh in restaurant.operating_hours}
    days_of_week_ordered = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    full_operating_hours = []
    for day in days_of_week_ordered:
        if day in operating_hours_display:
            full_operating_hours.append({
                'day': day,
                'open_time': operating_hours_display[day]['open_time'],
                'close_time': operating_hours_display[day]['close_time']
            })
        else:
            full_operating_hours.append({
                'day': day,
                'open_time': 'Closed',
                'close_time': None
            })

    is_saved_by_user = False
    # Check if the user is logged in before trying to access favourites
    if current_user.is_authenticated:
        # This is the most robust way to check for membership
        # when 'current_user.favourites' is an InstrumentedList (list-like)
        is_saved_by_user = restaurant in current_user.favourites

    return render_template('display.html', restaurant=restaurant,
                           status=status, status_detail=status_detail,
                           operating_hours=full_operating_hours,
                           is_saved_by_user=is_saved_by_user)


@app.route('/form', methods=['GET', 'POST'])
@login_required
def add_restaurant():
    if not current_user.is_admin:
        flash("Access denied. Admins only.", "error")
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']
        cuisine = request.form['cuisine']
        Maps_link = request.form['Maps_link']
        description = request.form['description']
        price = request.form['price']
        latitude = float(request.form['latitude'])
        longitude = float(request.form['longitude'])
        is_24_hours = 'all_week_24h' in request.form

        new_restaurant = Restaurant(
            name=name,
            address=address,
            phone=phone,
            cuisine=cuisine,
            Maps_link=Maps_link,
            description=description,
            price=price,
            latitude=latitude,
            longitude=longitude,
            is_24_hours=is_24_hours
        )
        db.session.add(new_restaurant)
        db.session.commit()

        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in days_of_week:
            open_time = None
            close_time = None

            if is_24_hours:
                open_time = '00:00'
                close_time = '00:00'
            else:
                closed_key = f"{day.lower()}_closed"
                open_time_key = f"{day.lower()}_open"
                close_time_key = f"{day.lower()}_close"

                if request.form.get(closed_key):
                    open_time = 'Closed'
                    close_time = None
                else:
                    open_time = request.form.get(open_time_key)
                    close_time = request.form.get(close_time_key)
                    if not open_time or not close_time: # Basic validation
                        flash(f"Please provide both open and close times for {day} or mark as closed.", "warning")
                        # You might want to handle this more robustly, e.e.g., redirect back to form
                        return redirect(url_for('add_restaurant'))


            new_operating_hour = OperatingHour(
                restaurant_id=new_restaurant.id,
                day_of_week=day,
                open_time=open_time,
                close_time=close_time
            )
            db.session.add(new_operating_hour)

        # Handle initial image uploads for add restaurant
        images = request.files.getlist('images')
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        first_image_url = None

        for image in images:
            if image and allowed_file(image.filename):
                try:
                    original_filename = secure_filename(image.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
                    image_path = os.path.join(upload_folder, unique_filename)

                    image.save(image_path)
                    image_url = url_for('static', filename=f'uploads/{unique_filename}')
                    db.session.add(RestaurantImage(image_url=image_url, restaurant_id=new_restaurant.id))

                    if not first_image_url:
                        first_image_url = image_url

                except Exception as e:
                    flash(f"Error saving image {original_filename}: {str(e)}", "error")

        if first_image_url:
            new_restaurant.image_url = first_image_url
        else:
            new_restaurant.image_url = url_for('static', filename='default.jpg')

        db.session.commit()
        flash("Restaurant Added Successfully!", "success")
        return redirect(url_for('display_restaurant', restaurant_id=new_restaurant.id))

    return render_template('form.html', operating_hours_data={})

@app.route("/delete-restaurant/<int:restaurant_id>", methods=["POST"])
@login_required
def delete_restaurant(restaurant_id):
    if not current_user.is_admin:
        flash("Unauthorized", "error")
        return redirect(url_for('index'))

    restaurant = Restaurant.query.get_or_404(restaurant_id)
    db.session.delete(restaurant)
    db.session.commit()
    flash("Restaurant deleted.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/edit-restaurant/<int:restaurant_id>', methods=['GET', 'POST'])
@login_required
def edit_restaurant(restaurant_id):
    if not current_user.is_admin:
        flash("Access denied. Admins only.", category='error')
        return redirect(url_for('index'))

    restaurant = Restaurant.query.get_or_404(restaurant_id)

    if request.method == 'POST':
        # Update restaurant details
        restaurant.name = request.form['name']
        restaurant.address = request.form['address']
        restaurant.phone = request.form['phone']
        restaurant.cuisine = request.form['cuisine']
        restaurant.Maps_link = request.form['Maps_link']
        restaurant.description = request.form['description']
        restaurant.price = request.form['price']
        restaurant.latitude = float(request.form['latitude'])
        restaurant.longitude = float(request.form['longitude'])
        restaurant.is_24_hours = 'all_week_24h' in request.form

        # Handle operating hours update
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in days_of_week:
            operating_hour = OperatingHour.query.filter_by(restaurant_id=restaurant.id, day_of_week=day).first()
            if not operating_hour:
                operating_hour = OperatingHour(restaurant_id=restaurant.id, day_of_week=day)
                db.session.add(operating_hour)

            if restaurant.is_24_hours:
                operating_hour.open_time = '00:00'
                operating_hour.close_time = '00:00'
            else:
                closed_key = f"{day.lower()}_closed"
                open_time_key = f"{day.lower()}_open"
                close_time_key = f"{day.lower()}_close"

                if request.form.get(closed_key):
                    operating_hour.open_time = 'Closed'
                    operating_hour.close_time = None
                else:
                    open_time = request.form.get(open_time_key)
                    close_time = request.form.get(close_time_key)
                    if not open_time or not close_time:
                        flash(f"Please provide both open and close times for {day} or mark as closed.", "warning")
                        return redirect(url_for('edit_restaurant', restaurant_id=restaurant.id))
                    operating_hour.open_time = open_time
                    operating_hour.close_time = close_time

        # Handle image uploads for edit restaurant (can add new ones, but existing are not deleted via this form)
        images = request.files.getlist('images')
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        first_image_url_from_upload = None

        for image in images:
            if image and allowed_file(image.filename):
                try:
                    original_filename = secure_filename(image.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
                    image_path = os.path.join(upload_folder, unique_filename)

                    image.save(image_path)
                    new_image_url = url_for('static', filename=f'uploads/{unique_filename}')
                    db.session.add(RestaurantImage(image_url=new_image_url, restaurant_id=restaurant.id))

                    if not first_image_url_from_upload:
                        first_image_url_from_upload = new_image_url # Keep track of the first new upload

                except Exception as e:
                    flash(f"Error saving image {original_filename}: {str(e)}", "error")

        # Update the main restaurant image_url if a new one was uploaded and existing was default
        if first_image_url_from_upload and restaurant.image_url == url_for('static', filename='default.jpg'):
            restaurant.image_url = first_image_url_from_upload
        # If no main image exists and new images were uploaded, set the first new one as main
        elif not restaurant.image_url and first_image_url_from_upload:
            restaurant.image_url = first_image_url_from_upload


        db.session.commit()
        flash("Restaurant details updated!", "success")
        return redirect(url_for('display_restaurant', restaurant_id=restaurant.id))

    # For GET request, prepare operating hours data to pre-fill the form
    operating_hours_data = {oh.day_of_week: oh for oh in restaurant.operating_hours}
    # Ensure all days are represented for the template, even if no data exists yet
    days_of_week_ordered = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for day in days_of_week_ordered:
        if day not in operating_hours_data:
            operating_hours_data[day] = OperatingHour(day_of_week=day, open_time='', close_time='') # Default empty

    return render_template('edit_restaurant.html', restaurant=restaurant, operating_hours_data=operating_hours_data)

@app.route('/favourite/<int:id>', methods=['POST'])
@login_required
def favourite(id):
    restaurant = Restaurant.query.get_or_404(id)
    if restaurant not in current_user.favourites:
        current_user.favourites.append(restaurant)
        db.session.commit()
        flash("Added to favourites!", category='success')
    else:
        flash("Already in favourites.", category='info')
    return redirect(url_for('index'))

@app.route('/unfavourite/<int:id>')
@login_required
def unfavourite(id):
    restaurant = Restaurant.query.get_or_404(id)
    if restaurant in current_user.favourites:
        current_user.favourites.remove(restaurant)
        db.session.commit()
        flash("Removed from favourites.", category='warning')
    return redirect(url_for('favourites_page'))

@app.route('/favourites')
@login_required
def favourites_page():
    return render_template('favourites.html', user=current_user, favourites=current_user.favourites)

@app.route('/toggle_save/<int:restaurant_id>', methods=['POST'])
@login_required
def toggle_save(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    if restaurant in current_user.favourites:
        current_user.favourites.remove(restaurant)
        db.session.commit()
        flash("Removed from favourites!", category='warning')
    else:
        current_user.favourites.append(restaurant)
        db.session.commit()
        flash("Added to favourites!", category='success')
    return redirect(request.referrer or url_for('display_restaurant', restaurant_id=restaurant_id))

# NEW ROUTE FOR UPLOADING ADDITIONAL PHOTOS
@app.route('/upload_photos/<int:restaurant_id>', methods=['GET', 'POST'])
@login_required
def upload_photos(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)

    if request.method == 'POST':
        images = request.files.getlist('images')
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        uploaded_count = 0
        for image in images:
            if image and allowed_file(image.filename):
                try:
                    original_filename = secure_filename(image.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
                    image_path = os.path.join(upload_folder, unique_filename)

                    image.save(image_path)
                    image_url = url_for('static', filename=f'uploads/{unique_filename}')

                    # Add new image to the RestaurantImage table
                    db.session.add(RestaurantImage(image_url=image_url, restaurant_id=restaurant.id))
                    uploaded_count += 1

                except Exception as e:
                    flash(f"Error saving image {image.filename}: {str(e)}", "error")
            elif image and not allowed_file(image.filename):
                flash(f"File {image.filename} is not allowed. Only PNG, JPG, JPEG are supported.", "warning")

        if uploaded_count > 0:
            db.session.commit()
            flash(f"Successfully uploaded {uploaded_count} new photo(s)!", "success")
        else:
            flash("No new photos were uploaded or selected.", "info")

        return redirect(url_for('display_restaurant', restaurant_id=restaurant.id))

    return render_template('upload_photos.html', restaurant=restaurant)

@app.route('/delete-image/<int:image_id>', methods=['POST'])
@login_required
def delete_image(image_id):
    if not current_user.is_admin:
        flash("Access denied. Admins only.", category='error')
        return redirect(url_for('index'))

    image = RestaurantImage.query.get_or_404(image_id)
    restaurant_id = image.restaurant_id

    # Get the restaurant to update its main image_url if the deleted image was the main one
    restaurant = Restaurant.query.get_or_404(restaurant_id)

    try:
        # Delete the image file from the server
        # Construct the full path to the image file
        filename = image.image_url.split('/')[-1]
        image_path = os.path.join(current_app.root_path, 'static', 'uploads', filename)
        if os.path.exists(image_path):
            os.remove(image_path)
            flash(f"Image file '{filename}' deleted from server.", "info")
        else:
            flash(f"Image file '{filename}' not found on server.", "warning")

        db.session.delete(image)
        db.session.commit()

        # If the deleted image was the main image_url for the restaurant, update it
        if restaurant.image_url == image.image_url:
            # Find another image for this restaurant to be the new main image
            # Or set to default if no other images exist
            remaining_images = RestaurantImage.query.filter_by(restaurant_id=restaurant.id).first()
            if remaining_images:
                restaurant.image_url = remaining_images.image_url
            else:
                restaurant.image_url = url_for('static', filename='default.jpg')
            db.session.commit()
            flash("Restaurant's main image updated.", "info")

        flash("Image removed successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting image: {str(e)}", "error")

    return redirect(url_for('display_restaurant', restaurant_id=restaurant_id))

@app.route('/restaurant/<int:restaurant_id>/review', methods=['POST'])
@login_required # <--- ADD THIS LINE
def submit_review(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    rating = int(request.form['rating'])
    text = request.form['text']

    author = current_user.username

    review = Review(restaurant_id=restaurant.id, rating=rating, text=text, author=author)
    db.session.add(review)
    db.session.commit()
    flash('Your review has been submitted!', "success")
    return redirect(url_for('display_restaurant', restaurant_id=restaurant.id))

@app.route('/mark-past/<int:id>')
@login_required
def mark_past(id):
    restaurant = Restaurant.query.get_or_404(id)
    if restaurant not in current_user.past:
        current_user.past_visits.append(restaurant)
        db.session.commit()
        flash("Marked as visited.", category='info')
    else:
        flash("Already marked as visited.", category='info')
    return redirect(url_for('index')) 

# Inside your app.py

@app.route('/past')
@login_required
def past_page():
    return render_template('past_restaurants.html', user=current_user, past_restaurants=current_user.past_visits)

@app.route('/unmark_past/<int:id>')
@login_required
def unmark_past(id):
    restaurant = Restaurant.query.get_or_404(id)
    if restaurant in current_user.past_visits:
        current_user.past_visits.remove(restaurant)
        db.session.commit()
        flash("Removed from visited restaurants.", "warning")
    return redirect(url_for('past_page'))

@app.route('/random', methods=['GET', 'POST'])
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

@app.route('/notes', methods=['GET', 'POST'])
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

@app.route('/past-restaurants')
@login_required
def past_restaurants():
    # current_user.past automatically gives you the list of associated Restaurant objects
    return render_template('past.html', user=current_user)

@app.route('/collections', methods=['GET', 'POST'])
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
        return redirect(url_for('collections')) # Redirect to prevent form resubmission

    # For GET requests, render the page with the user's collections
    return render_template('collections.html', user=current_user)


# NEW: Route to view the details of a single collection
@app.route('/collections/<int:collection_id>')
@login_required
def collection_detail(collection_id):
    collection = Collection.query.get_or_404(collection_id)
    # Ensure the collection belongs to the current user
    if collection.user_id != current_user.id:
        flash("You do not have permission to view this collection.", category='error')
        return redirect(url_for('views.collections'))

    return render_template('collection_detail.html', user=current_user, collection=collection)

@app.route('/add-to-collection', methods=['POST'])
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

    return redirect(request.referrer or url_for('random_restaurant'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
