from flask import Flask, redirect, render_template, request, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Float # import float
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure, random key in production!

# image upload folder
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# database config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'  # Use a proper database URL in production
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# models
class Restaurant(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200))
    phone = Column(String(20))
    cuisine = Column(String(100))
    google_maps_link = Column(String(300))
    description = Column(Text)
    photo_url = Column(String(300))
    is_saved = Column(Boolean, default=False)
    latitude = Column(Float, nullable=True) # add latitude
    longitude = Column(Float, nullable=True) # add longitude

    @property 
    def average_rating(self):
        """
        Calculates the average rating for the restaurant based on its reviews.

        Returns:
            float: The average rating, or None if there are no reviews.
        """
        reviews = self.reviews  # access the reviews using the backref
        if reviews:
            return sum(review.rating for review in reviews) / len(reviews)
        return None

    def __repr__(self):
        return f'<Restaurant {self.name}>'


class Review(db.Model):
    id = Column(Integer, primary_key=True)
    restaurant_id = Column(Integer, ForeignKey('restaurant.id'), nullable=False)
    rating = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    author = Column(String(100))  
    restaurant = relationship('Restaurant', backref=backref('reviews', lazy=True)) # set up relationship between the review & restaurant models
    def __repr__(self):
        return f'<Review by {self.author or "Anonymous"} for Restaurant {self.restaurant_id}>'
    
# NEW: Flask CLI command to initialize the database
@app.cli.command("init-db")
def init_db_command():
    """Clear existing data and create new tables."""
    with app.app_context():
        db.drop_all()  # Optional: Drops all existing tables. Useful for a clean start in development.
        db.create_all()
    print("Database initialized (tables created).")


# route
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form['name']
        cuisine = request.form['cuisine']
        description = request.form['description']
        address = request.form['address']
        phone = request.form['phone']
        google_maps_link = request.form['google_maps_link']
        latitude = request.form.get('latitude', None) # get latitude (use .get() to avoid KeyError)
        longitude = request.form.get('longitude', None)  # get longitude

        images = request.files.getlist('images')  
        image_urls = []

        for image_file in images:
            if image_file and allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image_file.save(image_path)
                image_urls.append(url_for('static', filename='uploads/' + filename))

        # joins all the urls into one string separated by commas
        photo_url = ','.join(image_urls) if image_urls else None

        new_restaurant = Restaurant(
            name=name,
            cuisine=cuisine,
            description=description,
            address=address,
            phone=phone,
            google_maps_link=google_maps_link,
            photo_url=photo_url,
            latitude=latitude,       
            longitude=longitude   
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
    author = request.form.get('author')  # author

    review = Review(restaurant_id=restaurant.id, rating=rating, text=text, author=author)
    db.session.add(review)
    db.session.commit()
    flash('Your review has been submitted!')
    return redirect(url_for('display_restaurant', restaurant_id=restaurant.id))


def allowed_file(filename):
    """Checks if the file extension is allowed (jpg, jpeg, png, gif)."""
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # create new tables
    app.run(debug=True)
