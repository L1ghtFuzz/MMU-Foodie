from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def home():
    CurrentRestaurants = [
        "Namo Garden", "Giggles & Geeks", "Woodfire Cyberjaya", 
        "Lengis Restaurant Cyberjaya", "Kocha Lala", "After Seven Lounge", 
        "10gram Cyberjaya", "Strawberry Fields Cafe Cyberjaya"
    ]
    html = """
    <html>
    <head><title>Restaurants</title></head>
    <body style="font-family: Arial; padding: 20px;">
      <h2>Current Restaurants List</h2>
      <ul>
        {% for restaurant in restaurants %}
          <li>{{ restaurant }}</li>
        {% endfor %}
      </ul>
    </body>
    </html>
    """
    return render_template_string(home, restaurants=CurrentRestaurants)

if __name__ == '__main__':
    app.run(debug=True)