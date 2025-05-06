from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os

# Initialize Flask app
app = Flask(__name__)

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max upload size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# ========== Models ==========

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    cuisine = db.Column(db.String(100))
    google_maps_link = db.Column(db.String(300))
    rating = db.Column(db.Integer)
    description = db.Column(db.Text)
    images = db.relationship('RestaurantImage', backref='restaurant', lazy=True)

    def __repr__(self):
        return f"<Restaurant {self.name}>"

class RestaurantImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300))
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)

# ========== Routes ==========

# Route for form page (add restaurant)
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']
        cuisine = request.form['cuisine']
        google_maps_link = request.form['google_maps_link']
        rating = int(request.form['rating'])
        description = request.form['description']

        # Create restaurant
        new_restaurant = Restaurant(
            name=name,
            address=address,
            phone=phone,
            cuisine=cuisine,
            google_maps_link=google_maps_link,
            rating=rating,
            description=description
        )
        db.session.add(new_restaurant)
        db.session.commit()

        # Handle image upload
        if 'image' in request.files:
            image = request.files['image']
            if image and image.filename != '':
                filename = secure_filename(image.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(filepath)

                new_image = RestaurantImage(filename=filename, restaurant_id=new_restaurant.id)
                db.session.add(new_image)
                db.session.commit()

        return redirect(url_for('restaurant_detail', restaurant_id=new_restaurant.id))

    return render_template('form.html')

# Restaurant detail page
@app.route('/restaurant/<int:restaurant_id>')
def restaurant_detail(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    return render_template('restaurant_detail.html', restaurant=restaurant)

# Upload additional image to existing restaurant
@app.route('/restaurant/<int:restaurant_id>/upload', methods=['POST'])
def upload_image(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)

    if 'image' not in request.files:
        return "No image part", 400

    file = request.files['image']
    if file.filename == '':
        return "No selected file", 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    new_image = RestaurantImage(filename=filename, restaurant_id=restaurant.id)
    db.session.add(new_image)
    db.session.commit()

    return redirect(url_for('restaurant_detail', restaurant_id=restaurant.id))

# ========== Run App ==========

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
