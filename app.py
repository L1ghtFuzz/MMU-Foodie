import random
from flask import Flask, render_template, request, redirect, flash, url_for, current_app
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from flask_login import LoginManager
from sqlalchemy.sql import func
from math import radians, cos, sin, sqrt, atan2
import re, os, uuid


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.secret_key = 'your_secret_key'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Optional

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Data Classes
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    favourites = db.relationship('Restaurant', secondary='favourites', backref='liked_by')
    is_admin = db.Column(db.Boolean, default=False)

favourites = db.Table('favourites',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('restaurant_id', db.Integer, db.ForeignKey('restaurant.id'))
)

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    cuisine = db.Column(db.String(100))
    price = db.Column(db.String(4))
    Maps_link = db.Column(db.String(300)) # Ensure this is 'Maps_link'
    description = db.Column(db.Text)
    image_url = db.Column(db.String(300))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    is_saved = db.Column(db.Boolean, default=False)
    reviews = db.relationship('Review', backref='restaurant', lazy=True)
    images = db.relationship('RestaurantImage', backref='restaurant', cascade='all, delete-orphan')
    @property
    def average_rating(self):
        reviews = self.reviews  # access the reviews using the backref
        if reviews:
            return sum(review.rating for review in reviews) / len(reviews)
        return None
    def __repr__(self):
        return f'<Restaurant {self.name}>'

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

user_favourites = set()
user_past = set()
user_reviews = {}

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
        # Filter restaurants by name (case-insensitive)
        query = query.filter(Restaurant.name.ilike(f'%{search_term}%'))

    min_rating = request.args.get('rating', type=int)
    price = request.args.get('price')
    category_param = request.args.get('category') 

    user_lat = request.args.get('user_lat', type=float)
    user_lon = request.args.get('user_lon', type=float)
    distance_limit = request.args.get('distance')

    def haversine(lat1, lon1, lat2, lon2):
        from math import radians, cos, sin, sqrt, atan2
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

    results = query.all()
    restaurants = []

    for restaurant, avg_rating in results:
        restaurant.avg_rating = round(avg_rating or 0, 1)

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
        return redirect(url_for('home'))

    restaurants = Restaurant.query.all()
    return render_template("admin-dashboard.html", user=current_user, restaurants=restaurants)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']

        # Allow login using either username or email
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
            return redirect(url_for('dashboard'))

    return render_template("sign-up.html", user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/favourite/<int:id>')
@login_required
def favourite(id):
    user_favourites.add(id)
    flash("Added to favourites!", category='success')
    return redirect(url_for('index'))

@app.route('/unfavourite/<int:id>')
@login_required
def unfavourite(id):
    user_favourites.discard(id)
    flash("Removed from favourites.", category='warning')
    return redirect(url_for('favourites_page'))

@app.route('/favourites')
@login_required
def favourites_page():
    favourites = [r for r in db.session.query(Restaurant).all() if r.id in user_favourites]
    return render_template('favourites.html', user=current_user, favourites=favourites)

@app.route('/mark-past/<int:id>')
@login_required
def mark_past(id):
    user_past.add(id)
    flash("Marked as visited.", category='info')
    return redirect(url_for('index'))

@app.route('/past')
@login_required
def past_page():
    past_restaurants = [r for r in db.session.query(Restaurant).all() if r.id in user_past]
    return render_template('past_restaurants.html', user=current_user, past_restaurants=past_restaurants)

@app.route('/random', methods=['GET', 'POST'])
@login_required
def random_restaurant():
    selected = None
    if request.method == 'POST':
        selected = Restaurant.query.order_by(func.random()).first()
    return render_template("random.html", user=current_user, selected=selected)

# Restaurant Things
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

@app.route('/restaurant/<int:restaurant_id>')
def display_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    return render_template('display.html', restaurant=restaurant)

@app.route('/form', methods=['GET', 'POST'])
@login_required
def add_restaurant():
    if not current_user.is_admin:
        flash("Access denied. Admins only.")
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

        new_restaurant = Restaurant(
            name=name,
            address=address,
            phone=phone,
            cuisine=cuisine,
            Maps_link=Maps_link,
            description=description,
            price=price,
            latitude=latitude,
            longitude=longitude
        )
        db.session.add(new_restaurant)
        db.session.commit()  # commit to get ID

        print("DEBUG - request.files:", request.files)
        print("DEBUG - images from form:", request.files.getlist('images'))

        images = request.files.getlist('images')
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        first_image_url = None # Initialize a variable to store the first image URL

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
        flash("Restaurant Added Successfully!")
        return redirect(url_for('display_restaurant', restaurant_id=new_restaurant.id))

    return render_template('form.html')

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
        # Update the restaurant details with the form data
        restaurant.name = request.form['name']
        restaurant.address = request.form['address']
        restaurant.phone = request.form['phone']
        restaurant.cuisine = request.form['cuisine']
        restaurant.Maps_link = request.form['Maps_link']
        restaurant.description = request.form['description']
        restaurant.price = request.form['price']
        restaurant.latitude = float(request.form['latitude'])
        restaurant.longitude = float(request.form['longitude'])

        # Handle image uploads
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
                    db.session.add(RestaurantImage(image_url=image_url, restaurant_id=restaurant.id))

                    if not first_image_url:
                        first_image_url = image_url

                except Exception as e:
                    flash(f"Error saving image {original_filename}: {str(e)}", "error")

        if first_image_url:
            restaurant.image_url = first_image_url
        elif not restaurant.image_url:
             restaurant.image_url = url_for('static', filename='default.jpg')

        db.session.commit()
        flash("Restaurant details updated!", "success")
        return redirect(url_for('display_restaurant', restaurant_id=restaurant.id))

    return render_template('edit_restaurant.html', restaurant=restaurant)

@app.route('/restaurant/<int:restaurant_id>/review', methods=['POST'])
def submit_review(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    rating = int(request.form['rating'])
    text = request.form['text']
    author = request.form.get('author')  # author
    review = Review(restaurant_id=restaurant.id, rating=rating, text=text, author=author)
    db.session.add(review)
    db.session.commit()
    flash('Your review has been submitted!')
    return redirect(url_for('display_restaurant', restaurant_id=restaurant.id))

@app.route('/restaurant/<int:restaurant_id>/save', methods=['POST'])
def toggle_save(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    restaurant.is_saved = not restaurant.is_saved
    db.session.commit()
    return redirect(url_for('display_restaurant', restaurant_id=restaurant.id))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)