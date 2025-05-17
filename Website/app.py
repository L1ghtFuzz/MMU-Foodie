from flask import Flask, render_template, request, redirect, session, jsonify, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from flask_login import LoginManager
import re, os

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
class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    cuisine = db.Column(db.String(100))
    price = db.Column(db.String(4))
    google_maps_link = db.Column(db.String(300))
    rating = db.Column(db.Integer)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(300))


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

@app.route("/base")
def base():
    return render_template('base.html')

@app.route('/')
def index():
    price = request.args.get('price')  # like '1,2,3'
    category = request.args.get('category')  # like 'Western,Chinese'
    rating = request.args.get('rating', type=float)  # like 4.5

    query = Restaurant.query

    if price:
        price_list = price.split(',')
        query = query.filter(Restaurant.price.in_(price_list))

    if category:
        category_list = category.split(',')
        query = query.filter(Restaurant.cuisine.in_(category_list))

    if rating:
        query = query.filter(Restaurant.rating >= rating)

    restaurants = query.all()
    return render_template('home.html', restaurants=restaurants)

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
            return redirect(url_for('admin-dashboard') if user.is_admin else url_for('home'))
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

 #Filter Function#
@app.route('/filter', methods=['POST'])
def filter_restaurants():
    filters = request.json
    query = Restaurant.query

    if 'price' in filters and filters['price']:
        query = query.filter(Restaurant.price.in_(filters['price']))

    if 'category' in filters and filters['category']:
        query = query.filter(Restaurant.category.in_(filters['category']))

    if 'rating' in filters:
        query = query.filter(Restaurant.rating >= filters['rating'])

    results = query.all()
    return jsonify([
        {
            'name': r.name,
            'price': r.price,
            'category': r.category,
            'rating': r.rating,
            'image_url': r.image_url
        } for r in results
    ])

@app.route('/restaurant/<int:restaurant_id>')
def display_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    return render_template('display.html', restaurant=restaurant)


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/add-restaurant', methods=['GET', 'POST'])
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

@app.route('/favourite/<int:id>')
@login_required
def favourite(id):
    restaurant = Restaurant.query.get_or_404(id)
    if restaurant not in current_user.favourites:
        current_user.favourites.append(restaurant)
        db.session.commit()
        flash("Added to favourites!", category='success')
    return redirect(url_for('/')) 

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



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
