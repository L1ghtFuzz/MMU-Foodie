from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy


# Initialize Flask app
app = Flask(__name__)

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Example model: Restaurant
class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    cuisine = db.Column(db.String(100))
    google_maps_link = db.Column(db.String(300))
    rating = db.Column(db.Integer)  
    
    def __repr__(self):
        return f"<Restaurant {self.name}>"

# Define a basic route
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']
        cuisine = request.form['cuisine']
        google_maps_link = request.form['google_maps_link']
        rating = int(request.form['rating'])

        new_restaurant = Restaurant(
            name=name,
            address=address,
            phone=phone,
            cuisine=cuisine,
            google_maps_link=google_maps_link,
            rating=rating
        )

        db.session.add(new_restaurant)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('form.html')


# Run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Creates the database tables if they don't exist
    app.run(debug=True)
