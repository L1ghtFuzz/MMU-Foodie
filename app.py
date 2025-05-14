from flask import Flask, redirect, render_template, request, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Image upload folder
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    cuisine = db.Column(db.String(100))
    google_maps_link = db.Column(db.String(300))
    rating = db.Column(db.Integer)
    description = db.Column(db.Text)
    photo_url = db.Column(db.String(300))
    is_saved = db.Column(db.Boolean, default=False)

    @property
    def average_rating(self):
        reviews = self.reviews
        if reviews:
            return sum([r.rating for r in reviews]) / len(reviews)
        return None

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100))
    restaurant = db.relationship('Restaurant', backref=db.backref('reviews', lazy=True))
    
    

# Routes

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

        # Handle image upload
        image_file = request.files.get('images')
        if image_file and image_file.filename != '':
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            photo_url = url_for('static', filename='uploads/' + filename)
        else:
            photo_url = None

        new_restaurant = Restaurant(
            name=name,
            address=address,
            phone=phone,
            cuisine=cuisine,
            google_maps_link=google_maps_link,
            rating=rating,
            description=description,
            photo_url=photo_url
        )

        db.session.add(new_restaurant)
        db.session.commit()

        flash("Restaurant Added Successfully!")
        return redirect(url_for('display_restaurant', restaurant_id=new_restaurant.id))

    return render_template('form.html')


@app.route('/restaurant/<int:restaurant_id>')
def display_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    return render_template('display.html', restaurant=restaurant)


@app.route('/restaurant/<int:restaurant_id>/save', methods=['POST'])
def toggle_save(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    restaurant.is_saved = not restaurant.is_saved
    db.session.commit()
    return redirect(url_for('display_restaurant', restaurant_id=restaurant.id))


@app.route('/restaurant/<int:restaurant_id>/review', methods=['POST'])
def submit_review(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    rating = int(request.form['rating'])
    text = request.form['text']
    author = request.form.get('author')  # Optional

    review = Review(restaurant_id=restaurant.id, rating=rating, text=text, author=author)
    db.session.add(review)
    db.session.commit()

    flash("Review submitted successfully!")
    return redirect(url_for('display_restaurant', restaurant_id=restaurant.id))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
