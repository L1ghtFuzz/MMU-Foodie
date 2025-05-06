from flask import Flask, render_template, request, redirect, session, jsonify
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_admin import Admin


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app)
admin = Admin()
admin.init_app(app)


    
#Data Class ~ Row of data
class MyAdmin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(10), default='user')  # 'admin' or 'user'

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.String(4))  
    category = db.Column(db.String(20))  
    rating = db.Column(db.Float)  
    link = db.Column(db.String(200)) 


# Routes to Webpages

@app.route("/base")
def base():
    return render_template('base.html')

@app.route("/")
def map_view():
    return render_template("index.html")


# Login Identification (Admin Or User)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']

        # Try matching by username or email
        user = MyAdmin.query.filter(
            (MyAdmin.username == identifier) | (MyAdmin.email == identifier)
        ).first()

        if user and user.password == password:
            # Login success
            session['username'] = user.username
            session['role'] = user.role
            return redirect('/admin' if user.role == 'admin' else '/dashboard')
        else:
            return 'Invalid credentials'

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/')
    return render_template('dashboard.html', username=session['username'])

@app.route('/admin')
def admin():
    if 'username' not in session or session['role'] != 'admin':
        return redirect('/')
    return render_template('admin.html', username=session['username'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

 # Restaurant Filters
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


# Runner and Debugger
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)