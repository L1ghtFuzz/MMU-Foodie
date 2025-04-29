from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('restaurants.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            rating INTEGER NOT NULL,
            address TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('form.html')

@app.route('/add_restaurant', methods=['POST'])
def add_restaurant():
    name = request.form['name']
    address = request.form['address']
    phone = request.form['phone_number']
    maps_link = request.form['google_maps_link']
    culinary_type_id = request.form['culinary_type_id']
    rating = request.form['rating']

    conn = sqlite3.connect('restaurants.db')
    c = conn.cursor()
    c.execute("INSERT INTO restaurants (name, category, rating, address) VALUES (?, ?, ?, ?)",
          (name, culinary_type_id, rating, address))
    conn.commit()
    conn.close()

    return "Restaurant added successfully!"

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
