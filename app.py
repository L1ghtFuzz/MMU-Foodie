from flask import Flask, redirect, render_template, request, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for flash()

# Database config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Model
class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    cuisine = db.Column(db.String(100))
    google_maps_link = db.Column(db.String(300))
    rating = db.Column(db.Integer)
    description = db.Column(db.Text)

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

        flash("Restaurant Added Successfully!")
        return redirect(url_for('display_restaurant', restaurant_id=new_restaurant.id))

    return render_template('form.html')

@app.route('/restaurant/<int:restaurant_id>')
def display_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    return render_template('display.html', restaurant=restaurant)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
